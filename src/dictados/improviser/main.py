"""Musical Improviser — CLI entry point.

Usage
-----
1. **Text input** (inline):
   ``python -m dictados.improviser.main "4 compases de Am C Dm E"``

2. **Text input with options**:
   ``python -m dictados.improviser.main "2 ruedas de Am C Dm E, swing, 130bpm"``

3. **MIDI file input**:
   ``python -m dictados.improviser.main --input input/my_chords.mid``

4. **Interactive mode** (no arguments):
   ``python -m dictados.improviser.main``

Optional flags
--------------
--tempo   INT     Override tempo in BPM (default: 120 or from text/MIDI).
--rounds  INT     Number of times to repeat the chord progression (default: 1 or from text).
--seed    INT     Random seed for reproducible output (default: random).
--output  PATH    Output MIDI file path (default: auto-generated in 01_midi_files/output/).
--style   STRING  Style hint: straight, swing, latin, blues (default: straight).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dictados.domain.chord import Chord
from dictados.improviser.chord_track import build_chord_track
from dictados.improviser.engine import ImproEngine
from dictados.improviser.melody_builder import build_melody_phrase
from dictados.improviser.midi_chord_reader import read_chords_from_midi
from dictados.improviser.text_parser import ParsedProgression, parse_text
from dictados.improviser.theory import chord_label
from dictados.midi.exporter import MidiExporter


# ─── Output path helper ───────────────────────────────────────────────────────

def _default_output_path(chords: list[Chord]) -> Path:
    timestamp = datetime.now().strftime("%d_%b_%Y_%H_%M").lower()
    chord_str = "_".join(chord_label(c) for c in chords[:4])
    output_dir = Path("01_midi_files") / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find next sequence number.
    max_num = 0
    for p in output_dir.glob("*.mid"):
        parts = p.stem.split("_")
        if parts[0].isdigit():
            max_num = max(max_num, int(parts[0]))
    seq = max_num + 1

    return output_dir / f"{seq:02d}_improviser_{chord_str}_{timestamp}.mid"


# ─── Core generation logic ────────────────────────────────────────────────────

def generate_improvisation(
    chords: list[Chord],
    tempo_bpm: int = 120,
    ppqn: int = 480,
    seed: Optional[int] = None,
    output_path: Optional[Path] = None,
    time_sig: str = "4/4",
    melody_velocity: int = 100,
) -> Path:
    """Generate a two-track MIDI file with chord backing and melodic improvisation.

    Args:
        chords:      Ordered list of chords (one per measure, already repeated).
        tempo_bpm:   Tempo in BPM.
        ppqn:        Pulses per quarter note.
        seed:        Random seed (None for non-deterministic).
        output_path: Where to write the output MIDI.  Auto-generated if None.
        time_sig:    Time signature string, e.g. ``"4/4"``.
        melody_velocity: MIDI velocity for the melody track.

    Returns:
        The path of the generated MIDI file.
    """
    num, den = map(int, time_sig.split("/"))

    # ── Build chord track (Track 1) ───────────────────────────────────────────
    chord_phrase = build_chord_track(chords, ppqn=ppqn, time_sig_num=num)

    # ── Generate melodic improvisation (Track 2) ──────────────────────────────
    engine = ImproEngine(ppqn=ppqn, time_sig_num=num, seed=seed)
    per_measure = engine.improvise(chords, start_midi=60)
    melody_phrase = build_melody_phrase(per_measure, chords, ppqn=ppqn, velocity=melody_velocity)

    # ── Export two-track MIDI ─────────────────────────────────────────────────
    if output_path is None:
        output_path = _default_output_path(chords)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    MidiExporter.export_two_track(
        melody=melody_phrase,
        accompaniment=chord_phrase,
        tempo_bpm=tempo_bpm,
        output_path=output_path,
        time_signature=(num, den),
        key="C",               # cosmetic key signature
        melody_program=73,     # MIDI program 73 = Flute (bright single-voice melody)
        accompaniment_program=0,  # program 0 = Acoustic Grand Piano
    )

    return output_path


# ─── Interactive mode ─────────────────────────────────────────────────────────

def _interactive() -> tuple[list[Chord], int, int, Optional[int]]:
    """Ask the user step-by-step and return (chords, tempo, rounds, seed)."""
    print("\n🎵  Musical Improviser — Interactive Mode")
    print("─" * 45)
    print("Examples of chord progressions:")
    print("  Am C Dm E")
    print("  Dm G7 Cmaj7 Am")
    print("  C Am F G\n")

    while True:
        raw = input("Enter chord progression (e.g. 'Am C Dm E'): ").strip()
        if raw:
            break
        print("  ⚠️  Please enter at least one chord.\n")

    while True:
        rounds_raw = input("How many rounds/repetitions? [1]: ").strip() or "1"
        if rounds_raw.isdigit() and int(rounds_raw) >= 1:
            rounds = int(rounds_raw)
            break
        print("  ⚠️  Please enter a positive integer.\n")

    while True:
        bpm_raw = input("Tempo in BPM? [120]: ").strip() or "120"
        if bpm_raw.isdigit() and 40 <= int(bpm_raw) <= 300:
            tempo_bpm = int(bpm_raw)
            break
        print("  ⚠️  Please enter a value between 40 and 300.\n")

    seed_raw = input("Random seed for reproducibility? (leave blank for random): ").strip()
    seed = int(seed_raw) if seed_raw.isdigit() else None

    # Parse chords from the raw progression string.
    prog = parse_text(raw)
    return prog.chords, tempo_bpm, rounds, seed


# ─── Argument parser ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dictados.improviser.main",
        description="Generate a two-track MIDI file: chord backing + melodic improvisation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Free-text chord progression, e.g. '4 compases de Am C Dm E, 130bpm'",
    )
    parser.add_argument(
        "--input", "-i",
        metavar="FILE",
        help="Path to an input MIDI file (inside the 'input/' folder or elsewhere).",
    )
    parser.add_argument("--tempo", type=int, default=None, metavar="BPM", help="Override tempo.")
    parser.add_argument("--rounds", type=int, default=None, metavar="N", help="Repetitions of the progression.")
    parser.add_argument("--seed", type=int, default=None, metavar="INT", help="Random seed.")
    parser.add_argument("--output", "-o", metavar="PATH", help="Output MIDI path.")
    parser.add_argument("--style", default=None, metavar="STYLE", help="Style hint (swing, latin, …).")
    return parser


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    chords: list[Chord]
    tempo_bpm: int
    rounds: int
    ppqn: int = 480

    # ── Determine input mode ──────────────────────────────────────────────────
    if args.input:
        # MIDI file input.
        midi_path = Path(args.input)
        if not midi_path.is_absolute():
            midi_path = Path("input") / midi_path if not midi_path.exists() else midi_path

        print(f"📂  Reading MIDI file: {midi_path}")
        result = read_chords_from_midi(midi_path)
        chords = result.chords
        tempo_bpm = result.tempo_bpm
        ppqn = result.ppqn
        rounds = 1
        print(
            f"   Detected {len(chords)} measure(s) at {tempo_bpm} BPM "
            f"({result.time_signature})"
        )

    elif args.text:
        # Inline text input.
        prog = parse_text(args.text)
        chords = prog.chords
        tempo_bpm = prog.tempo_bpm
        rounds = prog.rounds

    elif not sys.stdin.isatty():
        # Piped text.
        piped = sys.stdin.read().strip()
        if piped:
            prog = parse_text(piped)
            chords = prog.chords
            tempo_bpm = prog.tempo_bpm
            rounds = prog.rounds
        else:
            parser.print_help()
            return
    else:
        # Interactive mode.
        chords, tempo_bpm, rounds, args.seed = _interactive()

    # ── Apply overrides ───────────────────────────────────────────────────────
    if args.tempo:
        tempo_bpm = args.tempo
    if args.rounds:
        rounds = args.rounds

    all_chords = chords * rounds
    output_path = Path(args.output) if args.output else None

    # ── Summary ───────────────────────────────────────────────────────────────
    chord_names = " | ".join(chord_label(c) for c in chords)
    print(f"\n🎼  Progression  : {chord_names}")
    print(f"🔁  Rounds       : {rounds}  ({len(all_chords)} measures total)")
    print(f"🎚️   Tempo        : {tempo_bpm} BPM")
    if args.seed is not None:
        print(f"🌱  Seed         : {args.seed}")

    # ── Generate ──────────────────────────────────────────────────────────────
    out = generate_improvisation(
        chords=all_chords,
        tempo_bpm=tempo_bpm,
        ppqn=ppqn,
        seed=args.seed,
        output_path=output_path,
        time_sig="4/4",
    )

    print(f"\n✅  Generated: {out}")
    print(f"   Track 1 — Chord backing  (piano, program 0)")
    print(f"   Track 2 — Melodic improv (flute, program 73)")


if __name__ == "__main__":
    main()
