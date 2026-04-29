"""Bigram (n-gram) Markov baseline — verifies that the dataset encodes learnable patterns.

Trains a bigram language model on ``interval`` tokens from the training split,
then measures **perplexity** on the validation split.

A perplexity significantly lower than the vocabulary size (49 distinct interval
values from −24 to +24) indicates that the dataset contains genuine melodic
patterns rather than random noise.

Usage::

    python -m tools.analysis.markov_baseline \\
        --train data/splits/train.jsonl \\
        --val   data/splits/val.jsonl

    # N-gram order (default bigram=2):
    python -m tools.analysis.markov_baseline --order 3
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────────

def _load_sequences(path: Path) -> list[list[int]]:
    """Return a list of interval sequences, one per example."""
    sequences: list[list[int]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
            except json.JSONDecodeError:
                continue
            seq = [
                tok["interval"]
                for tok in ex.get("melody", [])
                if tok.get("interval") is not None
            ]
            if len(seq) >= 2:
                sequences.append(seq)
    return sequences


# ──────────────────────────────────────────────────────────────────────────────
# N-gram model
# ──────────────────────────────────────────────────────────────────────────────

class NGramModel:
    """Simple add-alpha smoothed n-gram language model over interval tokens."""

    def __init__(self, order: int = 2, alpha: float = 0.01) -> None:
        self.order = order
        self.alpha = alpha
        # counts[context_tuple] → Counter of next tokens
        self.counts: dict[tuple[int, ...], Counter] = defaultdict(Counter)
        self.vocab: set[int] = set()

    def train(self, sequences: list[list[int]]) -> None:
        """Train the model on a list of interval sequences."""
        for seq in sequences:
            for token in seq:
                self.vocab.add(token)
            for i in range(len(seq) - self.order + 1):
                context = tuple(seq[i: i + self.order - 1])
                next_token = seq[i + self.order - 1]
                self.counts[context][next_token] += 1

    def log_prob(self, context: tuple[int, ...], token: int) -> float:
        """Return log P(token | context) with add-alpha smoothing."""
        vocab_size = max(len(self.vocab), 1)
        counter = self.counts.get(context, Counter())
        total = sum(counter.values())
        count = counter.get(token, 0)
        prob = (count + self.alpha) / (total + self.alpha * vocab_size)
        return math.log(prob)

    def perplexity(self, sequences: list[list[int]]) -> float:
        """Compute per-token perplexity on *sequences*."""
        total_log_prob = 0.0
        n_tokens = 0
        for seq in sequences:
            for i in range(self.order - 1, len(seq)):
                context = tuple(seq[i - self.order + 1: i])
                token = seq[i]
                total_log_prob += self.log_prob(context, token)
                n_tokens += 1
        if n_tokens == 0:
            return float("inf")
        avg_log_prob = total_log_prob / n_tokens
        return math.exp(-avg_log_prob)

    def top_transitions(self, n: int = 10) -> list[tuple[tuple[int, ...], int, int]]:
        """Return the *n* most frequent (context, token, count) transitions."""
        items = [
            (ctx, tok, cnt)
            for ctx, counter in self.counts.items()
            for tok, cnt in counter.items()
        ]
        items.sort(key=lambda x: -x[2])
        return items[:n]


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train an n-gram baseline and report perplexity.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--train", type=Path, default=Path("data/splits/train.jsonl"),
        help="Training split JSONL file.",
    )
    parser.add_argument(
        "--val", type=Path, default=Path("data/splits/val.jsonl"),
        help="Validation split JSONL file.",
    )
    parser.add_argument(
        "--order", type=int, default=2,
        help="N-gram order (2 = bigram, 3 = trigram, ...).",
    )
    parser.add_argument(
        "--alpha", type=float, default=0.01,
        help="Add-alpha (Laplace) smoothing factor.",
    )
    args = parser.parse_args(argv)

    if not args.train.exists():
        print(f"ERROR: training file '{args.train}' not found.", file=sys.stderr)
        return 1
    if not args.val.exists():
        print(f"ERROR: validation file '{args.val}' not found.", file=sys.stderr)
        return 1

    print(f"Loading training data from {args.train} …")
    train_seqs = _load_sequences(args.train)
    print(f"  {len(train_seqs):,} sequences, "
          f"{sum(len(s) for s in train_seqs):,} tokens.")

    print(f"Loading validation data from {args.val} …")
    val_seqs = _load_sequences(args.val)
    print(f"  {len(val_seqs):,} sequences, "
          f"{sum(len(s) for s in val_seqs):,} tokens.")

    model = NGramModel(order=args.order, alpha=args.alpha)
    print(f"\nTraining {args.order}-gram model (α={args.alpha}) …")
    model.train(train_seqs)
    print(f"  Vocabulary size: {len(model.vocab)} distinct intervals.")
    print(f"  Context types seen: {len(model.counts):,}.")

    train_ppl = model.perplexity(train_seqs)
    val_ppl = model.perplexity(val_seqs)

    print(f"\nPerplexity:")
    print(f"  Train: {train_ppl:.2f}")
    print(f"  Val:   {val_ppl:.2f}")
    print(f"  Uniform baseline (vocab={len(model.vocab)}): {float(len(model.vocab)):.2f}")

    if val_ppl < len(model.vocab) * 0.7:
        print("\n✓  Val perplexity is well below uniform baseline — dataset encodes real patterns.")
    elif val_ppl < len(model.vocab):
        print("\n~  Val perplexity is below uniform baseline — some patterns learned.")
    else:
        print("\n✗  Val perplexity ≥ uniform baseline — check dataset or add more data.")

    print("\nTop 10 most frequent transitions:")
    print(f"  {'Context':<20}  {'→ Token':>8}  {'Count':>8}")
    print(f"  {'-'*20}  {'-'*8}  {'-'*8}")
    for ctx, tok, cnt in model.top_transitions(10):
        print(f"  {str(ctx):<20}  {tok:>8}  {cnt:>8}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
