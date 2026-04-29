"""Chord-scale theory for the melodic improviser.

Provides:
- Extended MIDI range (C3-C6) for melodic improvisation.
- Chord name parsing (e.g. "Am", "G7", "Cmaj7").
- Chord-to-scale mappings for modal improvisation.
- Helper functions to get chord tones and scale tones as MIDI numbers.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.pitch import Pitch

_log = logging.getLogger(__name__)

# ─── Melodic range ────────────────────────────────────────────────────────────
# Standard MIDI: C3 = 48, C4 (middle C) = 60, C5 = 72, C6 = 84
IMPRO_MIN_MIDI = 48   # C3
IMPRO_MAX_MIDI = 84   # C6


def make_pitch(midi: int) -> Pitch:
    """Create a Pitch without triggering the 41-81 range guard."""
    return Pitch(midi_number=midi)


# ─── Pitch-class constants ─────────────────────────────────────────────────────
NOTE_TO_PC: dict[str, int] = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
    "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}

PC_TO_NAME: list[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Scale intervals (semitones from root) for each mode used in chord-scale theory.
SCALE_INTERVALS: dict[str, list[int]] = {
    "major":          [0, 2, 4, 5, 7, 9, 11],
    "minor":          [0, 2, 3, 5, 7, 8, 10],
    "dorian":         [0, 2, 3, 5, 7, 9, 10],
    "phrygian":       [0, 1, 3, 5, 7, 8, 10],
    "mixolydian":     [0, 2, 4, 5, 7, 9, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "blues":          [0, 3, 5, 6, 7, 10],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
}

# Default scale mode per chord quality.
_QUALITY_TO_SCALE: dict[ChordQuality, str] = {
    ChordQuality.MAJOR:       "major",
    ChordQuality.MINOR:       "minor",
    ChordQuality.DIMINISHED:  "phrygian",
    ChordQuality.DOM7:        "mixolydian",
    ChordQuality.MAJ7:        "major",
    ChordQuality.MIN7:        "dorian",
}


# ─── Chord name parser ─────────────────────────────────────────────────────────
def parse_chord_name(name: str) -> Chord:
    """Parse a chord name like 'Am', 'G7', 'Cmaj7', 'Dm7' into a Chord object.

    Slash chords like ``Am/E`` are treated as the chord above the slash
    (the bass note is ignored).  Unsupported extensions such as ``aug``,
    ``sus2``, ``sus4``, and ``dim7`` are logged as warnings and mapped to
    the nearest supported quality.

    The root Pitch is set to the lowest MIDI number with that pitch class
    inside [60, 71] (i.e. within octave 4) for reference purposes only;
    the actual MIDI octave is resolved when building voicings.
    """
    raw = name.strip()
    if not raw:
        raise ValueError("Empty chord name")

    # ── Strip slash-chord bass note (e.g. "Am/E" → "Am") ─────────────────────
    if "/" in raw:
        chord_part, bass_part = raw.split("/", 1)
        _log.warning(
            "Slash chord %r: bass note %r ignored — using chord %r",
            raw, bass_part, chord_part,
        )
        raw = chord_part.strip()

    # Determine root pitch class.
    if len(raw) >= 2 and raw[1] in ("#", "b"):
        root_str = raw[:2].upper().replace("b", "B")
        suffix = raw[2:]
    else:
        root_str = raw[0].upper()
        suffix = raw[1:]

    if root_str not in NOTE_TO_PC:
        raise ValueError(f"Unknown chord root: {root_str!r}")

    root_pc = NOTE_TO_PC[root_str]
    # Use MIDI 60 as base octave for reference root (C4).
    root_midi = 60 + ((root_pc - 0) % 12)

    suffix_lower = suffix.lower()
    if suffix_lower in ("maj7", "Δ7", "Δ"):
        quality = ChordQuality.MAJ7
    elif suffix_lower in ("m7", "min7", "-7"):
        quality = ChordQuality.MIN7
    elif suffix_lower in ("7",):
        quality = ChordQuality.DOM7
    elif suffix_lower in ("dim", "°", "o", "dim7"):
        quality = ChordQuality.DIMINISHED
    elif suffix_lower in ("m", "min", "-", "m7b5"):
        quality = ChordQuality.MINOR
        if suffix_lower == "m7b5":
            _log.warning(
                "Chord suffix %r (half-diminished) treated as MINOR — "
                "full m7b5 support is pending.",
                suffix,
            )
    elif suffix_lower in ("", "maj", "M"):
        quality = ChordQuality.MAJOR
    elif suffix_lower in ("aug", "+"):
        _log.warning(
            "Augmented chord %r treated as MAJOR — aug support is pending.",
            raw,
        )
        quality = ChordQuality.MAJOR
    elif suffix_lower in ("sus2", "sus4", "sus"):
        _log.warning(
            "Suspended chord %r treated as MAJOR — sus support is pending.",
            raw,
        )
        quality = ChordQuality.MAJOR
    else:
        _log.warning(
            "Unrecognised chord suffix %r in %r — defaulting to MAJOR.",
            suffix, raw,
        )
        quality = ChordQuality.MAJOR

    return Chord(root=make_pitch(root_midi), quality=quality)


def chord_label(chord: Chord) -> str:
    """Return a human-readable chord label like 'Am', 'G7'."""
    name = PC_TO_NAME[chord.root.pitch_class]
    q = chord.quality
    if q == ChordQuality.MINOR:
        return f"{name}m"
    if q == ChordQuality.MIN7:
        return f"{name}m7"
    if q == ChordQuality.DOM7:
        return f"{name}7"
    if q == ChordQuality.MAJ7:
        return f"{name}maj7"
    if q == ChordQuality.DIMINISHED:
        return f"{name}dim"
    return name  # MAJOR


# ─── Scale / chord-tone helpers ────────────────────────────────────────────────
def get_scale_intervals(chord: Chord) -> list[int]:
    """Return the scale intervals (from chord root) appropriate for this chord."""
    scale_name = _QUALITY_TO_SCALE.get(chord.quality, "major")
    return SCALE_INTERVALS[scale_name]


def get_chord_tone_pcs(chord: Chord) -> list[int]:
    """Return pitch classes of the chord's chord tones (triad + 7th if present)."""
    return chord.get_chord_pitch_classes()


def get_scale_tone_pcs(chord: Chord) -> list[int]:
    """Return pitch classes of the scale tones for the given chord."""
    root_pc = chord.root.pitch_class
    intervals = get_scale_intervals(chord)
    return [(root_pc + i) % 12 for i in intervals]


def get_chord_tones_in_range(
    chord: Chord,
    low_midi: int = IMPRO_MIN_MIDI,
    high_midi: int = IMPRO_MAX_MIDI,
) -> list[int]:
    """Return all MIDI numbers of chord tones within [low_midi, high_midi]."""
    chord_pcs = set(get_chord_tone_pcs(chord))
    return [m for m in range(low_midi, high_midi + 1) if m % 12 in chord_pcs]


def get_scale_tones_in_range(
    chord: Chord,
    low_midi: int = IMPRO_MIN_MIDI,
    high_midi: int = IMPRO_MAX_MIDI,
) -> list[int]:
    """Return all MIDI numbers of scale tones within [low_midi, high_midi]."""
    scale_pcs = set(get_scale_tone_pcs(chord))
    return [m for m in range(low_midi, high_midi + 1) if m % 12 in scale_pcs]


def get_chromatic_tones_in_range(
    low_midi: int = IMPRO_MIN_MIDI,
    high_midi: int = IMPRO_MAX_MIDI,
) -> list[int]:
    """Return all MIDI numbers within [low_midi, high_midi]."""
    return list(range(low_midi, high_midi + 1))


def nearest_chord_tone(midi: int, chord: Chord) -> int:
    """Return the nearest chord tone MIDI number to *midi*."""
    chord_tones = get_chord_tones_in_range(chord, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI)
    if not chord_tones:
        return midi
    return min(chord_tones, key=lambda m: abs(m - midi))


def nearest_scale_tone(midi: int, chord: Chord) -> int:
    """Return the nearest scale tone MIDI number to *midi*."""
    scale_tones = get_scale_tones_in_range(chord, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI)
    if not scale_tones:
        return midi
    return min(scale_tones, key=lambda m: abs(m - midi))
