"""Tests for tools.dataset.splitter."""
from __future__ import annotations

import pytest

from tools.dataset.splitter import split_examples


def _make_example(source: str, n: int = 1) -> list[dict]:
    return [
        {
            "source": source,
            "context_chords": ["C"],
            "melody": [{"interval": 0, "dur_bin": 4, "vel_bin": 2, "pos_16th": 0}],
            "meta": {"tempo_bpm": 120, "style": None, "difficulty": 1, "window_bars": 1},
        }
        for _ in range(n)
    ]


class TestSplitExamples:
    def _all_examples(self, n_sources=10, n_per_source=3):
        examples = []
        for i in range(n_sources):
            examples.extend(_make_example(f"source_{i:02d}.mid", n=n_per_source))
        return examples

    def test_no_leakage(self):
        """Each source file must appear in exactly one split."""
        examples = self._all_examples(n_sources=20)
        train, val, test = split_examples(examples, seed=42)

        train_sources = {e["source"] for e in train}
        val_sources = {e["source"] for e in val}
        test_sources = {e["source"] for e in test}

        assert train_sources.isdisjoint(val_sources), "train/val overlap"
        assert train_sources.isdisjoint(test_sources), "train/test overlap"
        assert val_sources.isdisjoint(test_sources), "val/test overlap"

    def test_all_examples_present(self):
        """No example should be lost during splitting."""
        examples = self._all_examples()
        train, val, test = split_examples(examples, seed=42)
        assert len(train) + len(val) + len(test) == len(examples)

    def test_approximate_ratios(self):
        examples = self._all_examples(n_sources=100, n_per_source=1)
        train, val, test = split_examples(examples, seed=7)
        total = len(examples)
        assert 0.70 <= len(train) / total <= 0.90
        assert 0.05 <= len(val) / total <= 0.20
        assert 0.05 <= len(test) / total <= 0.20

    def test_reproducible_with_same_seed(self):
        examples = self._all_examples(n_sources=30)
        a_train, a_val, a_test = split_examples(examples, seed=1)
        b_train, b_val, b_test = split_examples(examples, seed=1)
        assert [e["source"] for e in a_train] == [e["source"] for e in b_train]
        assert [e["source"] for e in a_val] == [e["source"] for e in b_val]

    def test_different_seeds_give_different_splits(self):
        examples = self._all_examples(n_sources=30)
        train_a, _, _ = split_examples(examples, seed=1)
        train_b, _, _ = split_examples(examples, seed=99)
        sources_a = {e["source"] for e in train_a}
        sources_b = {e["source"] for e in train_b}
        # Very unlikely to be identical with different seeds.
        assert sources_a != sources_b

    def test_single_source(self):
        """With only one source, everything goes to train."""
        examples = _make_example("only_one.mid", n=5)
        train, val, test = split_examples(examples, seed=42)
        assert len(train) + len(val) + len(test) == 5

    def test_empty_input(self):
        train, val, test = split_examples([], seed=42)
        assert train == []
        assert val == []
        assert test == []

    def test_augmented_variants_stay_together(self):
        """All augmented variants of a source must be in the same split."""
        examples = []
        for source_i in range(20):
            src = f"song_{source_i:02d}.mid"
            for aug_shift in range(12):
                ex = {
                    "source": src,
                    "context_chords": ["C"],
                    "melody": [{"interval": aug_shift % 5, "dur_bin": 4, "vel_bin": 2, "pos_16th": 0}],
                    "meta": {
                        "tempo_bpm": 120,
                        "style": None,
                        "difficulty": 1,
                        "window_bars": 1,
                        "augmentation": {"transpose_semitones": aug_shift, "tempo_factor": 1.0},
                    },
                }
                examples.append(ex)

        train, val, test = split_examples(examples, seed=42)
        train_sources = {e["source"] for e in train}
        val_sources = {e["source"] for e in val}
        test_sources = {e["source"] for e in test}

        # Check that each source's examples are all in the same split.
        for src in {e["source"] for e in examples}:
            in_train = src in train_sources
            in_val = src in val_sources
            in_test = src in test_sources
            assert sum([in_train, in_val, in_test]) == 1, \
                f"Source {src} appeared in multiple splits"
