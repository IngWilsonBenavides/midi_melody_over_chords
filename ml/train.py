"""Training CLI — fit the ChordConditionedNGram model from the dataset splits.

Usage::

    # From repo root:
    python -m ml.train --config configs/ml_config.yaml

    # Override params:
    python -m ml.train --train data/splits/train.jsonl \\
                       --val   data/splits/val.jsonl   \\
                       --order 3 --alpha 0.5 --seed 42

    # Generate dataset first if missing:
    python -m ml.train --config configs/ml_config.yaml --regenerate-dataset
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from ml.model.ngram import ChordConditionedNGram

# ── Repo root heuristic ────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))


def _load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _build_dataset(repo_root: Path) -> None:
    """Re-generate seed MIDIs and rebuild dataset splits."""
    print("Generating seed MIDIs …")
    subprocess.run(
        [sys.executable, "scripts/generate_seed_midis.py"],
        cwd=repo_root, check=True,
    )
    print("Building dataset splits …")
    subprocess.run(
        [
            sys.executable, "-m", "tools.dataset.build_dataset",
            "--input-dir", "data/raw",
            "--output-dir", "data",
            "--report",
        ],
        cwd=repo_root, check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train the ChordConditionedNGram model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=None,
                        help="Path to ml_config.yaml")
    parser.add_argument("--train", type=Path, default=None,
                        help="Training JSONL split (overrides config).")
    parser.add_argument("--val", type=Path, default=None,
                        help="Validation JSONL split (overrides config).")
    parser.add_argument("--order", type=int, default=None)
    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--model-out", type=Path, default=None,
                        help="Output path for the pickled model.")
    parser.add_argument("--regenerate-dataset", action="store_true",
                        help="Re-generate seed MIDIs + rebuild splits before training.")
    args = parser.parse_args(argv)

    # Merge config < CLI overrides.
    cfg: dict = {}
    if args.config and args.config.exists():
        cfg = _load_config(args.config)

    train_path = args.train or Path(cfg.get("train_split", "data/splits/train.jsonl"))
    val_path   = args.val   or Path(cfg.get("val_split",   "data/splits/val.jsonl"))
    order      = args.order if args.order is not None else int(cfg.get("order", 3))
    alpha      = args.alpha if args.alpha is not None else float(cfg.get("alpha", 0.5))
    seed       = args.seed  if args.seed  is not None else cfg.get("seed", 42)
    model_out  = args.model_out or Path(cfg.get("model_path", "models/ngram.pkl"))

    # Regenerate dataset if requested or if splits are missing.
    if args.regenerate_dataset or not train_path.exists():
        _build_dataset(_REPO_ROOT)

    if not train_path.exists():
        print(f"ERROR: training file '{train_path}' not found.", file=sys.stderr)
        print("Run with --regenerate-dataset to build it.", file=sys.stderr)
        return 1

    print(f"Training ChordConditionedNGram (order={order}, alpha={alpha}, seed={seed})")
    print(f"  Train: {train_path}")
    print(f"  Val:   {val_path}")

    model = ChordConditionedNGram(order=order, alpha=alpha, seed=seed)
    model.fit(train_path)

    print(f"  Vocab size:   {model.vocab_size()} (interval, dur_bin) pairs")
    print(f"  State count:  {model.state_count()} distinct context keys")

    if val_path.exists():
        train_ppl = model.perplexity(train_path)
        val_ppl   = model.perplexity(val_path)
        print(f"  Perplexity — train: {train_ppl:.2f}  val: {val_ppl:.2f}")
        uniform = model.vocab_size()
        if val_ppl < uniform * 0.7:
            print("  ✓ Val perplexity well below uniform baseline — real patterns learned.")
        elif val_ppl < uniform:
            print("  ~ Val perplexity below uniform — some patterns learned.")
        else:
            print("  ✗ Val perplexity ≥ uniform — check dataset size/quality.")
    else:
        print(f"  (validation file '{val_path}' not found — skipping perplexity)")

    model.save(model_out)
    print(f"  Model saved → {model_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
