"""Seed MIDI generator — converts phrase_library licks to MIDI files.

Creates one MIDI file per (lick, chord_root, style) combination.
Each file has two tracks:
  - Track 1: the melody (monophonic).
  - Track 2: a sustained chord in the bass register providing harmonic context
    so the extractor can detect the chord root.

Output goes to ``data/raw/<style>/lick_<N>_<root>.mid``.

Usage::

    python scripts/generate_seed_midis.py
    python scripts/generate_seed_midis.py --out-dir data/raw --ppqn 480 --velocity 80
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Allow running from repo root without installing. ─────────────────────────
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root / "src"))

import mido

# Lick categories from the phrase library.
from dictados.improviser.phrase_library import (
    DOMINANT_LICKS,
    MAJOR_LICKS,
    MINOR_LICKS,
    UNIVERSAL_LICKS,
)

# ─── Constants ────────────────────────────────────────────────────────────────

# All 12 roots by pitch-class name.
_ROOTS: list[tuple[str, int]] = [
    ("C", 0), ("Db", 1), ("D", 2), ("Eb", 3),
    ("E", 4), ("F", 5), ("Gb", 6), ("G", 7),
    ("Ab", 8), ("A", 9), ("Bb", 10), ("B", 11),
]

# Chord intervals (semitones from root) for each style.
# These are placed in the bass register to give harmonic context.
_STYLE_CHORD_INTERVALS: dict[str, list[int]] = {
    "minor":    [0, 3, 7],        # minor triad
    "major":    [0, 4, 7],        # major triad
    "dominant": [0, 4, 7, 10],    # dominant 7th
    "jazz":     [0, 3, 7, 10],    # minor 7th (universal/jazz)
}

# Map style → list of lick objects.
_STYLE_GROUPS: list[tuple[str, list]] = [
    ("minor",    MINOR_LICKS),
    ("major",    MAJOR_LICKS),
    ("dominant", DOMINANT_LICKS),
    ("jazz",     UNIVERSAL_LICKS),
]

# Melody sits around octave 4-5; chord bass sits at octave 2-3.
_MELODY_BASE_MIDI = 60   # C4 = middle C
_CHORD_BASE_MIDI  = 36   # C2 (bass register)
_RANGE_LOW  = 48  # C3
_RANGE_HIGH = 84  # C6
_DEFAULT_PPQN     = 480
_DEFAULT_VELOCITY = 80
_DEFAULT_TEMPO_BPM = 120


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _melody_midi(root_pc: int, interval: int) -> int:
    """Absolute MIDI pitch for a melody note given chord root and semitone interval."""
    root = _MELODY_BASE_MIDI + root_pc
    midi = root + interval
    while midi > _RANGE_HIGH:
        midi -= 12
    while midi < _RANGE_LOW:
        midi += 12
    return midi


def _chord_midi_notes(root_pc: int, chord_intervals: list[int]) -> list[int]:
    """MIDI pitches for the chord voicing in the bass register."""
    base = _CHORD_BASE_MIDI + root_pc
    return [base + iv for iv in chord_intervals]


def _lick_to_midi(
    lick: list[tuple[int, float]],
    root_pc: int,
    style: str,
    ppqn: int,
    velocity: int,
    tempo_bpm: float,
) -> mido.MidiFile:
    """Convert a single lick to a two-track MidiFile with melody + chord track."""
    tempo_us = int(60_000_000 / tempo_bpm)
    total_beats = sum(beats for _, beats in lick)
    total_ticks = round(total_beats * ppqn)

    mid = mido.MidiFile(ticks_per_beat=ppqn)

    # ── Track 0: tempo / time-signature meta ──────────────────────────────────
    meta_track = mido.MidiTrack()
    mid.tracks.append(meta_track)
    meta_track.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))
    meta_track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta_track.append(mido.MetaMessage("end_of_track", time=0))

    # ── Track 1: melody (monophonic) ──────────────────────────────────────────
    melody_track = mido.MidiTrack()
    mid.tracks.append(melody_track)

    events: list[tuple[int, str, int, int]] = []
    tick = 0
    for interval, beats in lick:
        dur = round(beats * ppqn)
        note = _melody_midi(root_pc, interval)
        events.append((tick, "note_on",  note, velocity))
        events.append((tick + dur, "note_off", note, 0))
        tick += dur

    events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))
    last = 0
    for abs_tick, msg_type, note, vel in events:
        melody_track.append(
            mido.Message(msg_type, note=note, velocity=vel, time=abs_tick - last)
        )
        last = abs_tick
    melody_track.append(mido.MetaMessage("end_of_track", time=0))

    # ── Track 2: sustained chord (polyphonic — used as harmonic context) ──────
    chord_track = mido.MidiTrack()
    mid.tracks.append(chord_track)

    chord_intervals = _STYLE_CHORD_INTERVALS.get(style, [0, 3, 7])
    chord_notes = _chord_midi_notes(root_pc, chord_intervals)
    chord_vel = max(1, velocity - 20)  # quieter than melody

    # note_on for all chord notes at tick 0.
    for n in chord_notes:
        chord_track.append(mido.Message("note_on", note=n, velocity=chord_vel, time=0))

    # note_off for all chord notes at end of lick.
    first = True
    for n in chord_notes:
        chord_track.append(
            mido.Message("note_off", note=n, velocity=0, time=total_ticks if first else 0)
        )
        first = False

    chord_track.append(mido.MetaMessage("end_of_track", time=0))
    return mid


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate seed MIDI files from phrase_library licks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("data/raw"),
        help="Root output directory (style subdirectories are created automatically).",
    )
    parser.add_argument(
        "--ppqn", type=int, default=_DEFAULT_PPQN,
        help="MIDI ticks per quarter note.",
    )
    parser.add_argument(
        "--velocity", type=int, default=_DEFAULT_VELOCITY,
        help="MIDI note velocity (0–127).",
    )
    parser.add_argument(
        "--tempos", type=float, nargs="+",
        default=[80.0, 100.0, 120.0, 140.0, 160.0],
        help="BPM values to generate for each lick/root combination.",
    )
    args = parser.parse_args(argv)

    out_dir: Path = args.out_dir
    n_files = 0

    for style, licks in _STYLE_GROUPS:
        style_dir = out_dir / style
        style_dir.mkdir(parents=True, exist_ok=True)

        for lick_idx, lick in enumerate(licks):
            for root_name, root_pc in _ROOTS:
                for tempo in args.tempos:
                    fname = f"lick_{lick_idx + 1:02d}_{root_name}_{int(tempo)}bpm.mid"
                    out_path = style_dir / fname
                    mid = _lick_to_midi(lick, root_pc, style, args.ppqn, args.velocity, tempo)
                    mid.save(str(out_path))
                    n_files += 1

    print(f"Generated {n_files} MIDI files under '{out_dir}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
