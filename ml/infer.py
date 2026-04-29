"""Inference pipeline — generate a monophonic melody over a chord progression.

Loads a trained ChordConditionedNGram model and emits a list of
``(midi_pitch | None, duration_ticks, velocity)`` events for each bar,
then exports a two-track MIDI file.

Track 0: chord accompaniment (simple root-position voicing)
Track 1: melody (model output)

Usage::

    python -m ml.infer --config configs/ml_config.yaml \\
                       --progression "Am Am Em Em Am Am Dm Dm" \\
                       --out outputs/ml_melody.mid

    python -m ml.infer --seed 99 --temperature 1.2 --swing \\
                       --out outputs/ml_swing.mid
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import mido
import yaml

from ml.model.ngram import ChordConditionedNGram
from ml.model.vocab import (
    bucket_interval,
    chord_quality_tag,
    dur_bin_to_ticks,
    pos_16th_to_beat_group,
    vel_bin_to_velocity,
)

# ── Repo root ──────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from dictados.improviser.theory import NOTE_TO_PC  # noqa: E402

# ── Constants ──────────────────────────────────────────────────────────────────
_DEFAULT_PPQN   = 480
_MELODY_LOW     = 48   # C3
_MELODY_HIGH    = 84   # C6
_CHORD_BASE     = 36   # C2 (bass register)

# Chord voicing intervals per quality tag.
_VOICING: dict[str, list[int]] = {
    "m":   [0, 3, 7],
    "M":   [0, 4, 7],
    "7":   [0, 4, 7, 10],
    "dim": [0, 3, 6],
    "?":   [0, 4, 7],
}


# ── Chord root lookup ──────────────────────────────────────────────────────────

def _chord_root_pc(chord_symbol: str) -> int:
    """Return pitch-class (0–11) for the root of a chord symbol."""
    s = chord_symbol.strip()
    if len(s) >= 2 and s[1] in ("#", "b"):
        root_str = s[:2].upper().replace("b", "B")
    else:
        root_str = s[0].upper()
    return NOTE_TO_PC.get(root_str, 0)


def _chord_root_midi(root_pc: int, base: int = 60) -> int:
    """Nearest MIDI note ≥ base with the given pitch class."""
    m = base + ((root_pc - base % 12) % 12)
    return m


# ── Interval → MIDI pitch ──────────────────────────────────────────────────────

def _interval_to_midi(
    interval: int,
    root_pc: int,
    prev_midi: Optional[int],
    low: int = _MELODY_LOW,
    high: int = _MELODY_HIGH,
) -> int:
    """Convert a chord-relative interval to an absolute MIDI pitch.

    Picks the octave closest to *prev_midi* (voice-leading), then clamps.
    """
    target_pc = (root_pc + interval) % 12
    if prev_midi is None:
        prev_midi = (low + high) // 2

    # Try octaves centred around prev_midi.
    best = prev_midi
    best_dist = 999
    for octave in range(2, 8):
        m = octave * 12 + target_pc
        if low <= m <= high:
            d = abs(m - prev_midi)
            if d < best_dist:
                best_dist = d
                best = m
    return max(low, min(high, best))


# ── Swing helper ──────────────────────────────────────────────────────────────

def _apply_swing(tick: int, ppqn: int, ratio: float = 0.67) -> int:
    """Shift *tick* to apply triplet swing (ratio=2/3 ≈ 0.67).

    Only affects even 8th-note positions (every other 8th-note grid point).
    Works by stretching the 1st 8th of each beat and compressing the 2nd.
    """
    beat_ticks = ppqn
    eighth = ppqn // 2
    if eighth == 0:
        return tick
    beat_pos = tick % beat_ticks
    beat_start = tick - beat_pos
    if beat_pos < eighth:
        # First 8th: stretch.
        new_pos = round(beat_pos * 2 * ratio)
    else:
        # Second 8th: compress.
        new_pos = round(2 * ratio * eighth + (beat_pos - eighth) * 2 * (1 - ratio))
    return beat_start + new_pos


# ── Bar generator ──────────────────────────────────────────────────────────────

def generate_bar(
    model: ChordConditionedNGram,
    chord_symbol: str,
    ppqn: int,
    temperature: float,
    prev_interval_bucket: Optional[int],
    prev_dur_bin: Optional[int],
    prev_midi: Optional[int],
) -> tuple[list[tuple[Optional[int], int, int]], Optional[int], Optional[int], Optional[int]]:
    """Generate one bar of notes for *chord_symbol*.

    Returns:
        events:              list of (midi_pitch | None, duration_ticks, velocity)
        new_prev_midi:       last played MIDI pitch (for voice-leading)
        new_prev_ibucket:    last interval bucket (for Markov state)
        new_prev_dur_bin:    last dur_bin (for Markov state)
    """
    q_tag    = chord_quality_tag(chord_symbol)
    root_pc  = _chord_root_pc(chord_symbol)
    bar_ticks = ppqn * 4  # 4/4

    events: list[tuple[Optional[int], int, int]] = []
    remaining = bar_ticks
    pos_16th = 0

    while remaining > 0:
        beat_group = pos_16th_to_beat_group(pos_16th)
        interval, dur_bin = model.sample_next(
            chord_quality=q_tag,
            beat_group=beat_group,
            prev_interval_bucket=prev_interval_bucket,
            prev_dur_bin=prev_dur_bin,
            temperature=temperature,
        )
        vel_bin = model.sample_velocity(q_tag, beat_group, temperature)

        dur_ticks = dur_bin_to_ticks(dur_bin, ppqn)
        dur_ticks = max(ppqn // 8, min(remaining, dur_ticks))  # clamp to bar

        velocity = vel_bin_to_velocity(vel_bin)

        if interval is None:
            # REST
            events.append((None, dur_ticks, 0))
            midi_out: Optional[int] = None
        else:
            midi_out = _interval_to_midi(interval, root_pc, prev_midi)
            events.append((midi_out, dur_ticks, velocity))
            prev_midi = midi_out

        prev_interval_bucket = bucket_interval(interval)
        prev_dur_bin = dur_bin
        remaining -= dur_ticks
        pos_16th = min(15, pos_16th + max(1, dur_ticks * 4 // ppqn))

    return events, prev_midi, prev_interval_bucket, prev_dur_bin


# ── MIDI export ────────────────────────────────────────────────────────────────

def export_two_track_midi(
    chord_progression: list[str],
    melody_bars: list[list[tuple[Optional[int], int, int]]],
    out_path: Path,
    tempo_bpm: float,
    ppqn: int,
    swing: bool = False,
) -> None:
    """Write a two-track MIDI file.

    Track 0: sustained chord accompaniment (bass register).
    Track 1: monophonic melody.
    """
    tempo_us = int(60_000_000 / tempo_bpm)
    mid = mido.MidiFile(ticks_per_beat=ppqn)

    # ── Meta track ──────────────────────────────────────────────────────────────
    meta = mido.MidiTrack()
    mid.tracks.append(meta)
    meta.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("end_of_track", time=0))

    bar_ticks = ppqn * 4

    # ── Track 1: chord accompaniment ────────────────────────────────────────────
    chord_track = mido.MidiTrack()
    mid.tracks.append(chord_track)
    chord_track.append(mido.MetaMessage("track_name", name="Chords", time=0))
    chord_track.append(mido.Message("program_change", program=0, time=0))  # piano

    chord_events: list[tuple[int, str, int, int]] = []
    t = 0
    for chord_sym in chord_progression:
        root_pc = _chord_root_pc(chord_sym)
        q_tag   = chord_quality_tag(chord_sym)
        voicing = _VOICING.get(q_tag, [0, 4, 7])
        base    = _chord_root_midi(root_pc, _CHORD_BASE)
        notes   = [base + iv for iv in voicing]
        vel     = 55
        for n in notes:
            chord_events.append((t,          "note_on",  n, vel))
            chord_events.append((t + bar_ticks, "note_off", n, 0))
        t += bar_ticks

    chord_events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))
    _write_delta_track(chord_track, chord_events)

    # ── Track 2: melody ─────────────────────────────────────────────────────────
    melody_track = mido.MidiTrack()
    mid.tracks.append(melody_track)
    melody_track.append(mido.MetaMessage("track_name", name="Melody", time=0))
    melody_track.append(mido.Message("program_change", program=73, time=0))  # flute

    melody_events: list[tuple[int, str, int, int]] = []
    t = 0
    for bar_events in melody_bars:
        for midi_pitch, dur_ticks, velocity in bar_events:
            if midi_pitch is not None:
                on_t  = _apply_swing(t, ppqn) if swing else t
                off_t = _apply_swing(t + dur_ticks, ppqn) if swing else t + dur_ticks
                melody_events.append((on_t,  "note_on",  midi_pitch, velocity))
                melody_events.append((off_t, "note_off", midi_pitch, 0))
            t += dur_ticks

    melody_events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))
    _write_delta_track(melody_track, melody_events)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(out_path))


def _write_delta_track(
    track: mido.MidiTrack,
    events: list[tuple[int, str, int, int]],
) -> None:
    last = 0
    for abs_t, msg_type, note, vel in events:
        track.append(mido.Message(msg_type, note=note, velocity=vel, time=abs_t - last))
        last = abs_t
    track.append(mido.MetaMessage("end_of_track", time=0))


# ── CLI ────────────────────────────────────────────────────────────────────────

def generate_midi(
    chord_progression: list[str],
    model_path: Path,
    out_path: Path,
    tempo_bpm: float = 100.0,
    ppqn: int = _DEFAULT_PPQN,
    temperature: float = 1.0,
    seed: Optional[int] = None,
    swing: bool = False,
) -> list[list[tuple[Optional[int], int, int]]]:
    """High-level function: load model, generate, export. Returns melody_bars."""
    model = ChordConditionedNGram.load(model_path)
    if seed is not None:
        model._rng.seed(seed)

    melody_bars = []
    prev_midi: Optional[int] = None
    prev_ibucket: Optional[int] = None
    prev_dur_bin: Optional[int] = None

    for chord_sym in chord_progression:
        bar_events, prev_midi, prev_ibucket, prev_dur_bin = generate_bar(
            model, chord_sym, ppqn, temperature,
            prev_ibucket, prev_dur_bin, prev_midi,
        )
        melody_bars.append(bar_events)

    export_two_track_midi(chord_progression, melody_bars, out_path, tempo_bpm, ppqn, swing)
    return melody_bars


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a monophonic melody over a chord progression.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--model", type=Path, default=None,
                        help="Path to pickled model (overrides config).")
    parser.add_argument("--progression", type=str, default=None,
                        help="Space-separated chord symbols, e.g. 'Am Am Em Em Am Am Dm Dm'.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output MIDI file path.")
    parser.add_argument("--tempo", type=float, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--swing", action="store_true")
    args = parser.parse_args(argv)

    cfg: dict = {}
    if args.config and args.config.exists():
        with args.config.open() as fh:
            cfg = yaml.safe_load(fh) or {}

    model_path  = args.model      or Path(cfg.get("model_path",  "models/ngram.pkl"))
    progression = (args.progression or cfg.get("progression", "Am Am Em Em Am Am Dm Dm"))
    if isinstance(progression, list):
        chords = progression
    else:
        chords = progression.split()
    out_path    = args.out        or Path(cfg.get("out_path", "outputs/ml_melody.mid"))
    tempo       = args.tempo      or float(cfg.get("tempo", 100.0))
    temperature = args.temperature if args.temperature is not None else float(cfg.get("temperature", 1.0))
    seed        = args.seed       if args.seed is not None       else cfg.get("seed", None)
    swing       = args.swing      or bool(cfg.get("swing", False))

    if not model_path.exists():
        print(f"ERROR: model '{model_path}' not found. Run `make train` first.", file=sys.stderr)
        return 1

    print(f"Generating melody … progression: {' '.join(chords)}")
    print(f"  tempo={tempo} BPM  temp={temperature}  seed={seed}  swing={swing}")

    generate_midi(chords, model_path, out_path, tempo, _DEFAULT_PPQN, temperature, seed, swing)
    print(f"  → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
