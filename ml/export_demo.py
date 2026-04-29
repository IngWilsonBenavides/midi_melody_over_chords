"""Demo generator — produces the complete A/B test set and evaluation report.

Generates:
    outputs/before.mid        — rule-based ImproEngine (no ML)
    outputs/after_seed_42.mid  \
    outputs/after_seed_43.mid   |
    outputs/after_seed_44.mid   |  ML model, 5 different seeds
    outputs/after_seed_45.mid   |
    outputs/after_seed_46.mid  /

Then computes evaluation metrics for every MIDI and writes:
    reports/demo_summary.md

Usage::

    python -m ml.export_demo --config configs/ml_config.yaml

    # Override progression or tempo:
    python -m ml.export_demo --progression "Dm Dm Am Am" --tempo 110
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import mido
import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from dictados.improviser.engine import ImproEngine                     # noqa: E402
from dictados.improviser.chord_track import build_chord_track          # noqa: E402
from dictados.improviser.melody_builder import build_melody_phrase     # noqa: E402
from dictados.improviser.theory import parse_chord_name                # noqa: E402
from dictados.midi.exporter import MidiExporter                       # noqa: E402

from ml.infer import generate_midi, export_two_track_midi              # noqa: E402
from ml.eval_metrics import compute_all                                # noqa: E402
from ml.model.ngram import ChordConditionedNGram                       # noqa: E402
from ml.model.vocab import chord_quality_tag, dur_bin_to_ticks, vel_bin_to_velocity  # noqa: E402
from ml.infer import generate_bar                                      # noqa: E402

_DEFAULT_PPQN = 480
_DEMO_SEEDS   = [42, 43, 44, 45, 46]


# ── "Before" generation (rule-based ImproEngine) ──────────────────────────────

def generate_before(
    chord_symbols: list[str],
    out_path: Path,
    tempo_bpm: float,
    ppqn: int,
    seed: Optional[int],
) -> list[tuple[Optional[int], int, int]]:
    """Generate rule-based melody and return flat event list."""
    chords = [parse_chord_name(s) for s in chord_symbols]
    chord_phrase = build_chord_track(chords, ppqn=ppqn, time_sig_num=4)
    engine = ImproEngine(ppqn=ppqn, time_sig_num=4, seed=seed)
    per_measure = engine.improvise(chords, start_midi=60)
    melody_phrase = build_melody_phrase(per_measure, chords, ppqn=ppqn, velocity=90)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    MidiExporter.export_two_track(
        melody=melody_phrase,
        accompaniment=chord_phrase,
        tempo_bpm=int(tempo_bpm),
        output_path=out_path,
        time_signature=(4, 4),
        key="C",
        melody_program=73,
        accompaniment_program=0,
    )

    # Extract flat events from the exported phrase.
    events: list[tuple[Optional[int], int, int]] = []
    for measure in melody_phrase.measures:
        for note in measure.notes:
            pitch = note.pitch.midi_number if (note.is_audible and note.pitch) else None
            dur   = note.end_tick - note.start_tick
            vel   = note.velocity
            events.append((pitch, dur, vel))
    return events


# ── "After" generation (ML model) ─────────────────────────────────────────────

def generate_after(
    chord_symbols: list[str],
    model_path: Path,
    out_path: Path,
    tempo_bpm: float,
    ppqn: int,
    temperature: float,
    seed: int,
) -> list[tuple[Optional[int], int, int]]:
    """Generate ML melody and return flat event list."""
    melody_bars = generate_midi(
        chord_progression=chord_symbols,
        model_path=model_path,
        out_path=out_path,
        tempo_bpm=tempo_bpm,
        ppqn=ppqn,
        temperature=temperature,
        seed=seed,
        swing=False,
    )
    return [ev for bar in melody_bars for ev in bar]


# ── Markdown report ────────────────────────────────────────────────────────────

def _fmt_metrics(m: dict) -> str:
    return (
        f"| ngram_rep_rate | {m['ngram_rep_rate']:.4f} |\n"
        f"| pitch_range_semitones | {m['pitch_range_semitones']} |\n"
        f"| large_leap_rate | {m['large_leap_rate']:.4f} |\n"
        f"| rhythmic_density | {m['rhythmic_density']:.2f} |\n"
        f"| in_scale_rate | {m['in_scale_rate']:.4f} |\n"
        f"| note_count | {m['note_count']} |\n"
        f"| rest_count | {m['rest_count']} |\n"
    )


def write_report(
    results: list[dict],
    report_path: Path,
    chord_symbols: list[str],
    tempo: float,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Demo Summary — ML Melodic Improviser\n")
    lines.append(f"**Progression:** {' '.join(chord_symbols)}  ")
    lines.append(f"**Tempo:** {tempo} BPM  ")
    lines.append(f"**Model:** Chord-Conditioned N-gram Markov\n")
    lines.append("---\n")
    lines.append("## How to listen\n")
    lines.append("Open any of the files in `outputs/` with a MIDI player:\n")
    lines.append("- **macOS**: GarageBand, QuickTime Player, or `afplay` (for MP3 exports)\n")
    lines.append("- **Windows**: Windows Media Player, MuseScore\n")
    lines.append("- **Linux**: TiMidity++, FluidSynth, MuseScore\n")
    lines.append("- **Online**: [midi.city](https://midi.city), [BeepBox](https://www.beepbox.co)\n\n")
    lines.append("## How to reproduce\n")
    lines.append("```bash\n")
    lines.append("# 1. Build dataset (if not already done):\n")
    lines.append("make dataset\n\n")
    lines.append("# 2. Train the model:\n")
    lines.append("make train\n\n")
    lines.append("# 3. Generate demo files + this report:\n")
    lines.append("make demo\n")
    lines.append("```\n\n")
    lines.append("---\n")
    lines.append("## Results\n\n")
    lines.append("| File | Type | Description |\n")
    lines.append("|------|------|-------------|\n")
    for r in results:
        lines.append(f"| `{r['file']}` | {r['type']} | {r['desc']} |\n")
    lines.append("\n---\n")
    lines.append("## Metrics per file\n\n")

    for r in results:
        lines.append(f"### {r['file']}\n\n")
        lines.append(f"**Type:** {r['type']}  \n")
        lines.append(f"**Description:** {r['desc']}  \n\n")
        lines.append("| Metric | Value |\n")
        lines.append("|--------|-------|\n")
        lines.append(_fmt_metrics(r["metrics"]))
        lines.append("\n")

    lines.append("---\n")
    lines.append("## Metric Definitions\n\n")
    lines.append("| Metric | Definition |\n")
    lines.append("|--------|------------|\n")
    lines.append("| `ngram_rep_rate` | Fraction of consecutive pitch 3-grams that repeat (0 = no repetition) |\n")
    lines.append("| `pitch_range_semitones` | Max − min MIDI pitch |\n")
    lines.append("| `large_leap_rate` | Fraction of melodic intervals > 7 semitones |\n")
    lines.append("| `rhythmic_density` | Mean distinct 16th-note onset positions per bar |\n")
    lines.append("| `in_scale_rate` | Fraction of pitches in A natural minor |\n")
    lines.append("| `note_count` | Total pitched notes |\n")
    lines.append("| `rest_count` | Total rests |\n")

    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"  Report written → {report_path}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate demo MIDIs and evaluation report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--progression", type=str, default=None)
    parser.add_argument("--tempo", type=float, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    cfg: dict = {}
    if args.config and args.config.exists():
        with args.config.open() as fh:
            cfg = yaml.safe_load(fh) or {}

    model_path  = args.model     or Path(cfg.get("model_path", "models/ngram.pkl"))
    progression = args.progression or cfg.get("progression", "Am Am Em Em Am Am Dm Dm")
    if isinstance(progression, list):
        chords = progression
    else:
        chords = progression.split()
    tempo       = args.tempo     or float(cfg.get("tempo", 100.0))
    temperature = args.temperature if args.temperature is not None else float(cfg.get("temperature", 1.0))
    out_dir     = args.out_dir   or Path(cfg.get("out_dir", "outputs"))
    report_path = args.report    or Path(cfg.get("report_path", "reports/demo_summary.md"))

    if not model_path.exists():
        print(f"ERROR: model '{model_path}' not found. Run `make train` first.", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    # ── Before (rule-based) ────────────────────────────────────────────────────
    before_path = out_dir / "before.mid"
    print(f"Generating BEFORE (rule-based) → {before_path}")
    before_events = generate_before(chords, before_path, tempo, _DEFAULT_PPQN, seed=0)
    results.append({
        "file": "before.mid",
        "type": "Rule-based (ImproEngine)",
        "desc": "Existing lick/arpeggio/scale-walk strategy engine — no ML",
        "metrics": compute_all(before_events, _DEFAULT_PPQN, len(chords)),
    })

    # ── After (ML) for 5 seeds ─────────────────────────────────────────────────
    for seed in _DEMO_SEEDS:
        fname = f"after_seed_{seed}.mid"
        after_path = out_dir / fname
        print(f"Generating AFTER  (ML, seed={seed}) → {after_path}")
        after_events = generate_after(
            chords, model_path, after_path, tempo, _DEFAULT_PPQN, temperature, seed
        )
        results.append({
            "file": fname,
            "type": f"ML (N-gram, seed={seed})",
            "desc": f"Chord-conditioned Markov model, temperature={temperature}",
            "metrics": compute_all(after_events, _DEFAULT_PPQN, len(chords)),
        })

    # ── Print summary table ────────────────────────────────────────────────────
    print("\n── Metrics summary ──────────────────────────────────────────────")
    header = f"{'File':<30}  {'rep':>6}  {'range':>5}  {'leaps':>5}  {'rhythm':>6}  {'scale':>5}"
    print(header)
    print("-" * len(header))
    for r in results:
        m = r["metrics"]
        print(
            f"{r['file']:<30}  "
            f"{m['ngram_rep_rate']:>6.3f}  "
            f"{m['pitch_range_semitones']:>5}  "
            f"{m['large_leap_rate']:>5.3f}  "
            f"{m['rhythmic_density']:>6.2f}  "
            f"{m['in_scale_rate']:>5.3f}"
        )

    write_report(results, report_path, chords, tempo)
    print(f"\n✓  Demo complete.  {len(results)} files in '{out_dir}/'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
