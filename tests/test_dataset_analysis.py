"""Tests for tools.analysis.stats and tools.analysis.markov_baseline."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tools.analysis.stats import compute_stats, compute_all_splits
from tools.analysis.markov_baseline import NGramModel, _load_sequences


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _write_jsonl(path: Path, examples: list[dict]) -> None:
    with path.open("w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


def _make_example(
    source="song.mid",
    intervals=None,
    style=None,
    difficulty=1,
    tempo=120.0,
    window_bars=4,
):
    intervals = intervals or [0, 2, 4, 0, -1, 3, 5, 0]
    melody = [
        {
            "interval": iv,
            "dur_bin": 2,
            "vel_bin": 2,
            "pos_16th": i % 16,
        }
        for i, iv in enumerate(intervals)
    ]
    return {
        "source": source,
        "context_chords": ["Am"],
        "melody": melody,
        "meta": {
            "tempo_bpm": tempo,
            "style": style,
            "difficulty": difficulty,
            "window_bars": window_bars,
            "key": "Am",
            "time_sig": "4/4",
            "augmentation": {"transpose_semitones": 0, "tempo_factor": 1.0},
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Stats tests
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeStats:
    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        stats = compute_stats(p)
        assert stats["n_examples"] == 0

    def test_basic_counts(self, tmp_path):
        examples = [_make_example(source=f"s{i}.mid") for i in range(5)]
        p = tmp_path / "train.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert stats["n_examples"] == 5
        assert stats["n_tokens"] == 5 * 8  # 8 tokens per example

    def test_interval_distribution_keys(self, tmp_path):
        examples = [_make_example(intervals=[0, 2, 4])]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert "interval_distribution" in stats
        # Intervals 0, 2, 4 should appear.
        dist = stats["interval_distribution"]
        assert "0" in dist
        assert "2" in dist
        assert "4" in dist

    def test_style_distribution(self, tmp_path):
        examples = [
            _make_example(style="jazz"),
            _make_example(style="jazz"),
            _make_example(style="blues"),
        ]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert stats["style_distribution"]["jazz"] == 2
        assert stats["style_distribution"]["blues"] == 1

    def test_difficulty_distribution(self, tmp_path):
        examples = [_make_example(difficulty=i % 5) for i in range(10)]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert "difficulty_distribution" in stats
        assert sum(stats["difficulty_distribution"].values()) == 10

    def test_tempo_stats(self, tmp_path):
        examples = [_make_example(tempo=float(t)) for t in [100, 120, 140]]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert stats["tempo_mean_bpm"] == pytest.approx(120.0, abs=1.0)
        assert stats["tempo_min_bpm"] == pytest.approx(100.0, abs=0.1)
        assert stats["tempo_max_bpm"] == pytest.approx(140.0, abs=0.1)

    def test_notes_per_bar(self, tmp_path):
        # 8 notes over 4 bars = 2 notes/bar.
        examples = [_make_example(intervals=list(range(8)), window_bars=4)]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert stats["notes_per_bar_mean"] == pytest.approx(2.0, abs=0.01)

    def test_chromatic_fraction(self, tmp_path):
        # All odd intervals (chromatic) → fraction = 1.0
        examples = [_make_example(intervals=[1, 3, 5, 7])]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        stats = compute_stats(p)
        assert stats["interval_chromatic_fraction"] == pytest.approx(1.0, abs=0.01)


class TestComputeAllSplits:
    def test_all_splits_loaded(self, tmp_path):
        for name in ("train", "val", "test"):
            p = tmp_path / f"{name}.jsonl"
            _write_jsonl(p, [_make_example()])

        result = compute_all_splits(tmp_path)
        assert set(result.keys()) == {"train", "val", "test"}
        for key in result:
            assert result[key]["n_examples"] == 1

    def test_missing_split_skipped(self, tmp_path):
        _write_jsonl(tmp_path / "train.jsonl", [_make_example()])
        result = compute_all_splits(tmp_path)
        assert "train" in result
        assert "val" not in result
        assert "test" not in result


# ──────────────────────────────────────────────────────────────────────────────
# Markov baseline tests
# ──────────────────────────────────────────────────────────────────────────────

class TestNGramModel:
    def test_train_and_perplexity(self):
        seqs = [[0, 2, 4, 2, 0], [0, 4, 7, 4, 0], [2, 4, 5, 4, 2]]
        model = NGramModel(order=2, alpha=0.01)
        model.train(seqs)
        assert len(model.vocab) > 0
        ppl = model.perplexity(seqs)
        assert ppl > 0
        assert ppl < len(model.vocab)  # better than random

    def test_perplexity_train_le_val(self):
        """Train perplexity should be ≤ validation perplexity."""
        train = [[0, 2, 4, 2, 0] * 5, [0, 4, 7, 4, 0] * 5]
        val = [[0, 2, 4, 2, 0], [3, 5, 7, 5, 3]]
        model = NGramModel(order=2, alpha=0.01)
        model.train(train)
        assert model.perplexity(train) <= model.perplexity(val) + 5

    def test_trigram(self):
        seqs = [[0, 2, 4, 5, 7, 5, 4, 2, 0]] * 10
        model = NGramModel(order=3, alpha=0.1)
        model.train(seqs)
        ppl = model.perplexity(seqs)
        assert ppl < len(model.vocab)

    def test_empty_sequence(self):
        model = NGramModel(order=2)
        model.train([])
        assert model.perplexity([]) == float("inf")

    def test_top_transitions(self):
        seqs = [[0, 2, 4, 0, 2, 4, 0, 2, 4]]
        model = NGramModel(order=2)
        model.train(seqs)
        top = model.top_transitions(3)
        assert len(top) <= 3
        # Most frequent transition: (2,) → 4
        assert top[0][2] >= 2  # count ≥ 2

    def test_log_prob_smoothed(self):
        """Unseen n-gram should have non-zero probability (add-alpha smoothing)."""
        seqs = [[0, 2, 4]]
        model = NGramModel(order=2, alpha=1.0)
        model.train(seqs)
        # Unseen context.
        lp = model.log_prob((99,), 99)
        assert lp < 0  # log prob < 0 (probability < 1)
        import math
        assert math.exp(lp) > 0  # strictly positive


class TestLoadSequences:
    def test_load_basic(self, tmp_path):
        examples = [
            _make_example(intervals=[0, 2, 4]),
            _make_example(intervals=[3, 5, 7]),
        ]
        p = tmp_path / "train.jsonl"
        _write_jsonl(p, examples)
        seqs = _load_sequences(p)
        assert len(seqs) == 2
        assert seqs[0] == [0, 2, 4]
        assert seqs[1] == [3, 5, 7]

    def test_skips_short_sequences(self, tmp_path):
        # Single-note sequences are not useful (need at least 2).
        examples = [_make_example(intervals=[0])]
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, examples)
        seqs = _load_sequences(p)
        assert len(seqs) == 0

    def test_null_intervals_excluded(self, tmp_path):
        ex = {
            "source": "t.mid",
            "melody": [
                {"interval": None, "dur_bin": 4, "vel_bin": 2, "pos_16th": 0},
                {"interval": 2, "dur_bin": 4, "vel_bin": 2, "pos_16th": 4},
                {"interval": 4, "dur_bin": 4, "vel_bin": 2, "pos_16th": 8},
            ],
            "meta": {},
        }
        p = tmp_path / "t.jsonl"
        _write_jsonl(p, [ex])
        seqs = _load_sequences(p)
        assert len(seqs) == 1
        assert None not in seqs[0]
