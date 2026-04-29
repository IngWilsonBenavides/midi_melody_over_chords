"""CLI dataset builder — orchestrates extract → normalise → tokenise → augment → split.

Usage::

    python -m tools.dataset.build_dataset \\
        --input-dir  data/raw \\
        --output-dir data \\
        --window-bars 4 \\
        --seed 42

    # Process only a specific style subdirectory:
    python -m tools.dataset.build_dataset \\
        --input-dir data/raw/jazz \\
        --style jazz \\
        --output-dir data

    # Dry-run (extract and normalise only, no output written):
    python -m tools.dataset.build_dataset --input-dir data/raw --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _iter_midi_files(input_dir: Path) -> list[tuple[Path, str | None]]:
    """Yield (midi_path, style_or_None) pairs from *input_dir*.

    Style is inferred from the immediate subdirectory name if it matches a
    known genre; otherwise ``None``.
    """
    known_styles = {
        "jazz", "blues", "rock", "pop", "classical", "fusion",
        "reggae", "latin", "folk", "country", "funk", "soul",
        "metal", "electronic", "r&b", "rb",
        "minor", "major", "dominant",
    }
    results: list[tuple[Path, str | None]] = []
    for midi_path in sorted(input_dir.rglob("*.mid")):
        style: str | None = midi_path.parent.name.lower()
        if style not in known_styles:
            style = None
        results.append((midi_path, style))
    # Also pick up .midi extension.
    for midi_path in sorted(input_dir.rglob("*.midi")):
        style = midi_path.parent.name.lower()
        if style not in known_styles:
            style = None
        results.append((midi_path, style))
    return results


def _write_jsonl(path: Path, examples: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"  → wrote {len(examples):,} examples to {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the melodic improviser training dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-dir", type=Path, default=Path("data/raw"),
        help="Root directory containing .mid files (searched recursively).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data"),
        help="Output root.  Processed examples go to <output-dir>/processed/; "
             "splits to <output-dir>/splits/.",
    )
    parser.add_argument(
        "--window-bars", type=int, default=4,
        help="Number of bars per training example window.",
    )
    parser.add_argument(
        "--style", type=str, default=None,
        help="Force a style tag for all files (overrides directory heuristic).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for train/val/test split.",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.80,
        help="Fraction of source files for training.",
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.10,
        help="Fraction of source files for validation.",
    )
    parser.add_argument(
        "--no-augment", action="store_true",
        help="Skip augmentation (useful for quick debugging).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract and normalise only; do not write output files.",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate reports/dataset_summary.md after building.",
    )

    args = parser.parse_args(argv)

    # Late imports to keep startup fast.
    from tools.dataset.extractor import extract_segments
    from tools.dataset.normalizer import normalise_segment
    from tools.dataset.tokenizer import tokenise_segment
    from tools.dataset.augmentor import augment_example
    from tools.dataset.splitter import split_examples

    input_dir: Path = args.input_dir
    if not input_dir.exists():
        print(f"ERROR: input directory '{input_dir}' does not exist.", file=sys.stderr)
        return 1

    midi_files = _iter_midi_files(input_dir)
    if not midi_files:
        print(f"WARNING: no .mid files found under '{input_dir}'.", file=sys.stderr)
        return 0

    print(f"Found {len(midi_files)} MIDI file(s) under '{input_dir}'.")

    all_examples: list[dict] = []
    n_segments = 0
    n_normalised = 0
    n_tokenised = 0

    for midi_path, file_style in midi_files:
        style = args.style or file_style
        print(f"  Processing {midi_path.name} (style={style!r}) …", end=" ")

        segments = extract_segments(midi_path, window_bars=args.window_bars, style=style)
        n_segments += len(segments)

        for seg in segments:
            norm = normalise_segment(seg)
            if norm is None:
                continue
            n_normalised += 1

            example = tokenise_segment(norm)
            if example is None:
                continue
            n_tokenised += 1

            if args.no_augment:
                all_examples.append(example)
            else:
                all_examples.extend(augment_example(example))

        print(f"{len(segments)} segments extracted.")

    print(
        f"\nSummary: {n_segments} raw segments → "
        f"{n_normalised} normalised → "
        f"{n_tokenised} tokenised → "
        f"{len(all_examples)} total examples (after augmentation)."
    )

    if args.dry_run:
        print("Dry-run mode: no output files written.")
        return 0

    if not all_examples:
        print("No examples produced. Check your input MIDI files.", file=sys.stderr)
        return 1

    # Write processed (all examples, unshuffled).
    processed_path = args.output_dir / "processed" / "all.jsonl"
    _write_jsonl(processed_path, all_examples)

    # Split and write.
    train, val, test = split_examples(
        all_examples,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )
    splits_dir = args.output_dir / "splits"
    _write_jsonl(splits_dir / "train.jsonl", train)
    _write_jsonl(splits_dir / "val.jsonl", val)
    _write_jsonl(splits_dir / "test.jsonl", test)

    print(
        f"\nSplit sizes: train={len(train):,}  val={len(val):,}  test={len(test):,}"
    )

    if args.report:
        from tools.analysis.generate_report import generate_report
        report_path = Path("reports") / "dataset_summary.md"
        generate_report(splits_dir, report_path)
        print(f"Report written to {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
