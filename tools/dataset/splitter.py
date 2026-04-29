"""Train/val/test splitter — splits examples by source file to prevent leakage.

Split ratios: 80% train / 10% val / 10% test.

Usage::

    from tools.dataset.splitter import split_examples

    train, val, test = split_examples(all_examples, seed=42)
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any


def split_examples(
    examples: list[dict[str, Any]],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Split *examples* into train / val / test sets by source file.

    All examples derived from the same source MIDI (including augmented
    variants) are kept in the same split to prevent data leakage.

    Args:
        examples:     List of tokenised (and augmented) training examples.
        train_ratio:  Fraction of source files assigned to training set.
        val_ratio:    Fraction of source files assigned to validation set.
                      The remainder goes to test.
        seed:         Random seed for reproducible shuffling.

    Returns:
        Three lists: (train_examples, val_examples, test_examples).
    """
    # Group examples by their *original* source (ignore augmentation shift).
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ex in examples:
        by_source[ex["source"]].append(ex)

    sources = sorted(by_source.keys())
    rng = random.Random(seed)
    rng.shuffle(sources)

    n = len(sources)
    n_train = max(1, round(n * train_ratio))
    n_val = max(0, round(n * val_ratio))

    train_sources = set(sources[:n_train])
    val_sources = set(sources[n_train: n_train + n_val])
    # test = everything else

    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []

    for source, exs in by_source.items():
        if source in train_sources:
            train.extend(exs)
        elif source in val_sources:
            val.extend(exs)
        else:
            test.extend(exs)

    return train, val, test
