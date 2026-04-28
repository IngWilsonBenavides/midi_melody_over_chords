"""MIDI chord reader.

Reads a MIDI file and attempts to detect one chord per measure from the
simultaneous / overlapping pitch classes in each measure window.

The detection algorithm:
1. Scan all notes in a measure window and collect their pitch classes.
2. Try to match the pitch-class set against common chord templates.
3. Return the best-matching :class:`~dictados.domain.chord.Chord` for each measure.

This works best with MIDI files that contain explicit chord voicings
(e.g. piano left-hand comping).  For single-note melody tracks the
detected chords will be poor; in that case the user should use text input
instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mido

from dictados.domain.chord import Chord, ChordQuality
from dictados.improviser.theory import (
    make_pitch,
    PC_TO_NAME,
    NOTE_TO_PC,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)

# ─── Chord templates ──────────────────────────────────────────────────────────
# Each template is (quality, [intervals from root]).
_TEMPLATES: list[tuple[ChordQuality, list[int]]] = [
    (ChordQuality.MAJ7,       [0, 4, 7, 11]),
    (ChordQuality.MIN7,       [0, 3, 7, 10]),
    (ChordQuality.DOM7,       [0, 4, 7, 10]),
    (ChordQuality.MAJOR,      [0, 4, 7]),
    (ChordQuality.MINOR,      [0, 3, 7]),
    (ChordQuality.DIMINISHED, [0, 3, 6]),
]


def _match_score(pcs: set[int], root_pc: int, intervals: list[int]) -> int:
    """Count how many template intervals are present in *pcs*."""
    template_pcs = {(root_pc + iv) % 12 for iv in intervals}
    return len(template_pcs & pcs)


def _detect_chord(pcs: set[int]) -> Chord | None:
    """Return the best-matching Chord for a set of pitch classes, or None."""
    if not pcs:
        return None

    best_chord: Chord | None = None
    best_score = 0

    for root_pc in range(12):
        for quality, intervals in _TEMPLATES:
            score = _match_score(pcs, root_pc, intervals)
            # Require at least root + one other chord tone.
            if score >= 2 and score > best_score:
                best_score = score
                root_midi = 60 + root_pc  # reference octave (C4 = 60)
                best_chord = Chord(root=make_pitch(root_midi), quality=quality)

    return best_chord


# ─── Main reader ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ChordReaderResult:
    """Result from :func:`read_chords_from_midi`."""
    chords: list[Chord]      # One chord per detected measure
    tempo_bpm: int
    ppqn: int
    time_signature: str      # e.g. "4/4"


def read_chords_from_midi(midi_path: Path) -> ChordReaderResult:
    """Read a MIDI file and return one :class:`Chord` per measure.

    Args:
        midi_path: Path to the input ``.mid`` file.

    Returns:
        A :class:`ChordReaderResult` with the detected chords, tempo, etc.

    Raises:
        FileNotFoundError: If *midi_path* does not exist.
        ValueError: If no pitched notes are found in the file.
    """
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    midi = mido.MidiFile(str(midi_path))
    ppqn = midi.ticks_per_beat

    # ── Parse all note events ─────────────────────────────────────────────────
    tempo = 500000  # μs per beat → 120 bpm
    numerator, denominator = 4, 4

    raw_events: list[tuple[int, int]] = []  # (start_tick, pitch)

    for track in midi.tracks:
        abs_tick = 0
        active: dict[tuple[int, int], int] = {}  # (channel, pitch) → start_tick

        for msg in track:
            abs_tick += msg.time
            if msg.is_meta:
                if msg.type == "set_tempo":
                    tempo = msg.tempo
                elif msg.type == "time_signature":
                    numerator = msg.numerator
                    denominator = msg.denominator
                continue

            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = abs_tick
            elif msg.type in {"note_off", "note_on"}:
                key = (msg.channel, msg.note)
                if key in active:
                    start = active.pop(key)
                    # Filter to improviser range.
                    if IMPRO_MIN_MIDI <= msg.note <= IMPRO_MAX_MIDI:
                        raw_events.append((start, msg.note))

    if not raw_events:
        raise ValueError(
            "No pitched notes found in the MIDI file. "
            "Make sure it contains note events in the range MIDI 48–84."
        )

    # ── Segment into measures ─────────────────────────────────────────────────
    measure_ticks = int(numerator * ppqn * (4 / denominator))
    max_tick = max(start for start, _ in raw_events) + 1
    num_measures = max(1, (max_tick + measure_ticks - 1) // measure_ticks)

    chords: list[Chord] = []

    for m_idx in range(num_measures):
        m_start = m_idx * measure_ticks
        m_end = m_start + measure_ticks

        pcs: set[int] = set()
        for start_tick, pitch in raw_events:
            if m_start <= start_tick < m_end:
                pcs.add(pitch % 12)

        chord = _detect_chord(pcs)
        if chord is None:
            # Use previous chord if detection fails.
            chord = chords[-1] if chords else Chord(root=make_pitch(60), quality=ChordQuality.MAJOR)

        chords.append(chord)

    tempo_bpm = int(round(mido.tempo2bpm(tempo)))

    return ChordReaderResult(
        chords=chords,
        tempo_bpm=tempo_bpm,
        ppqn=ppqn,
        time_signature=f"{numerator}/{denominator}",
    )
