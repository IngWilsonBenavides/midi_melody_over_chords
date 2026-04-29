"""End-to-end tests for the ML improvisation pipeline.

These tests verify the full pipeline runs without error and that the
generated outputs have the expected structure and properties.

They are intentionally fast (using tiny datasets / short progressions)
so that CI can run them without requiring the full 43 k-example dataset.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────

_REPO = Path(__file__).resolve().parent.parent


def _tiny_jsonl(tmp_path: Path, n_examples: int = 20) -> Path:
    """Write a tiny JSONL dataset to *tmp_path* and return its path."""
    path = tmp_path / "train.jsonl"
    examples = []
    for _ in range(n_examples):
        examples.append({
            "source": "test",
            "context_chords": ["Am"],
            "melody": [
                {"interval": 0,  "dur_bin": 2, "vel_bin": 2, "pos_16th": 0},
                {"interval": 2,  "dur_bin": 2, "vel_bin": 2, "pos_16th": 2},
                {"interval": -1, "dur_bin": 2, "vel_bin": 2, "pos_16th": 4},
                {"interval": None,"dur_bin": 2, "vel_bin": 2, "pos_16th": 6},
                {"interval": 3,  "dur_bin": 4, "vel_bin": 3, "pos_16th": 8},
            ],
            "meta": {"style_tag": "neutral"},
        })
    with path.open("w") as fh:
        for ex in examples:
            fh.write(json.dumps(ex) + "\n")
    return path


# ── Vocab tests ────────────────────────────────────────────────────────────────

class TestVocab:
    def test_bucket_interval_zero(self):
        from ml.model.vocab import bucket_interval
        assert bucket_interval(0) == 0

    def test_bucket_interval_rest(self):
        from ml.model.vocab import bucket_interval
        assert bucket_interval(None) is None

    def test_bucket_interval_quantises(self):
        from ml.model.vocab import bucket_interval
        # Python banker's rounding: round(0.5) == 0, round(1.5) == 2
        assert bucket_interval(1) == 0    # 1/2=0.5 → rounds to 0
        assert bucket_interval(3) == 4    # 3/2=1.5 → rounds to 2 → *2 = 4
        assert bucket_interval(-3) == -4  # symmetric

    def test_chord_quality_tag_minor(self):
        from ml.model.vocab import chord_quality_tag
        assert chord_quality_tag("Am") == "m"
        assert chord_quality_tag("Dm") == "m"

    def test_chord_quality_tag_major(self):
        from ml.model.vocab import chord_quality_tag
        assert chord_quality_tag("C") == "M"
        assert chord_quality_tag("G") == "M"

    def test_chord_quality_tag_dom7(self):
        from ml.model.vocab import chord_quality_tag
        assert chord_quality_tag("G7") == "7"

    def test_dur_bin_to_ticks_roundtrip(self):
        from ml.model.vocab import dur_bin_to_ticks, ticks_to_dur_bin
        for b in range(8):
            ticks = dur_bin_to_ticks(b, ppqn=480)
            recovered = ticks_to_dur_bin(ticks, ppqn=480)
            assert recovered == b

    def test_pos_16th_to_beat_group(self):
        from ml.model.vocab import pos_16th_to_beat_group
        assert pos_16th_to_beat_group(0) == 0
        assert pos_16th_to_beat_group(4) == 1
        assert pos_16th_to_beat_group(8) == 2
        assert pos_16th_to_beat_group(12) == 3


# ── NGram model tests ──────────────────────────────────────────────────────────

class TestNGram:
    def test_fit_and_sample(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        data = _tiny_jsonl(tmp_path)
        model = ChordConditionedNGram(order=1, alpha=0.5, seed=0)
        model.fit(data)
        assert model.vocab_size() > 0
        assert model.state_count() > 0

        interval, dur_bin = model.sample_next(
            chord_quality="m",
            beat_group=0,
            prev_interval_bucket=None,
            prev_dur_bin=None,
            temperature=1.0,
        )
        assert dur_bin in range(8)
        assert interval is None or isinstance(interval, int)

    def test_sample_greedy(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        data = _tiny_jsonl(tmp_path, n_examples=50)
        model = ChordConditionedNGram(seed=42)
        model.fit(data)
        # Greedy (temperature=0) should be deterministic.
        r1 = model.sample_next(chord_quality="m", beat_group=0,
                               prev_interval_bucket=None, prev_dur_bin=None,
                               temperature=0.0)
        r2 = model.sample_next(chord_quality="m", beat_group=0,
                               prev_interval_bucket=None, prev_dur_bin=None,
                               temperature=0.0)
        assert r1 == r2

    def test_perplexity_lower_than_vocab(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        data = _tiny_jsonl(tmp_path, n_examples=100)
        model = ChordConditionedNGram(seed=42)
        model.fit(data)
        ppl = model.perplexity(data)
        assert ppl < model.vocab_size()

    def test_save_load_roundtrip(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        data = _tiny_jsonl(tmp_path)
        model = ChordConditionedNGram(seed=7)
        model.fit(data)
        pkl_path = tmp_path / "test_model.pkl"
        model.save(pkl_path)
        loaded = ChordConditionedNGram.load(pkl_path)
        assert loaded.vocab_size() == model.vocab_size()
        assert loaded.state_count() == model.state_count()

    def test_sample_velocity(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        data = _tiny_jsonl(tmp_path)
        model = ChordConditionedNGram(seed=0)
        model.fit(data)
        vel = model.sample_velocity("m", 0)
        assert 0 <= vel <= 4


# ── Inference tests ────────────────────────────────────────────────────────────

class TestInfer:
    def test_generate_bar(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        from ml.infer import generate_bar
        data = _tiny_jsonl(tmp_path, n_examples=50)
        model = ChordConditionedNGram(seed=0)
        model.fit(data)
        events, prev_midi, prev_ibucket, prev_dur_bin = generate_bar(
            model, "Am", ppqn=480, temperature=1.0,
            prev_interval_bucket=None, prev_dur_bin=None, prev_midi=None,
        )
        assert isinstance(events, list)
        assert len(events) > 0
        total_ticks = sum(d for _, d, _ in events)
        assert total_ticks == 480 * 4  # exactly one 4/4 bar

    def test_generate_midi_produces_file(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        from ml.infer import generate_midi
        data = _tiny_jsonl(tmp_path, n_examples=50)
        model = ChordConditionedNGram(seed=0)
        model.fit(data)
        model_path = tmp_path / "model.pkl"
        model.save(model_path)

        out_path = tmp_path / "test.mid"
        melody_bars = generate_midi(
            chord_progression=["Am", "Em"],
            model_path=model_path,
            out_path=out_path,
            tempo_bpm=100.0,
            ppqn=480,
            temperature=1.0,
            seed=42,
            swing=False,
        )
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        assert len(melody_bars) == 2  # one bar per chord

    def test_swing_midi_produces_file(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        from ml.infer import generate_midi
        data = _tiny_jsonl(tmp_path, n_examples=30)
        model = ChordConditionedNGram(seed=1)
        model.fit(data)
        model_path = tmp_path / "model.pkl"
        model.save(model_path)
        out_path = tmp_path / "swing.mid"
        generate_midi(["Am"], model_path, out_path, swing=True)
        assert out_path.exists()


# ── Evaluation metrics tests ───────────────────────────────────────────────────

class TestEvalMetrics:
    _EVENTS = [
        (60, 240, 80), (62, 240, 80), (64, 240, 80), (60, 240, 80),
        (62, 240, 80), (64, 240, 80), (None, 240, 0), (65, 240, 80),
    ]

    def test_ngram_rep_rate(self):
        from ml.eval_metrics import ngram_rep_rate
        rate = ngram_rep_rate(self._EVENTS)
        assert 0.0 <= rate <= 1.0

    def test_pitch_range(self):
        from ml.eval_metrics import pitch_range_semitones
        assert pitch_range_semitones(self._EVENTS) == 5

    def test_large_leap_rate(self):
        from ml.eval_metrics import large_leap_rate
        assert large_leap_rate(self._EVENTS) == 0.0

    def test_rhythmic_density(self):
        from ml.eval_metrics import rhythmic_density
        d = rhythmic_density(self._EVENTS, ppqn=480, bars=1)
        assert d > 0

    def test_in_scale_rate_am(self):
        from ml.eval_metrics import in_scale_rate
        # 60=C4, 62=D4, 64=E4, 65=F4 — all in A minor scale.
        rate = in_scale_rate(self._EVENTS)
        assert rate == 1.0

    def test_compute_all_keys(self):
        from ml.eval_metrics import compute_all
        metrics = compute_all(self._EVENTS, ppqn=480, bars=1)
        expected_keys = {
            "ngram_rep_rate", "pitch_range_semitones", "large_leap_rate",
            "rhythmic_density", "in_scale_rate", "note_count", "rest_count",
        }
        assert set(metrics.keys()) == expected_keys

    def test_empty_events(self):
        from ml.eval_metrics import compute_all
        metrics = compute_all([], ppqn=480, bars=8)
        assert metrics["note_count"] == 0
        assert metrics["in_scale_rate"] == 1.0

    def test_rest_count(self):
        from ml.eval_metrics import compute_all
        metrics = compute_all(self._EVENTS)
        assert metrics["rest_count"] == 1


# ── Full pipeline smoke test ───────────────────────────────────────────────────

class TestPipelineEndToEnd:
    """Smoke test: train → infer → metrics, no file-system side effects outside tmp."""

    def test_full_pipeline(self, tmp_path):
        from ml.model.ngram import ChordConditionedNGram
        from ml.infer import generate_midi
        from ml.eval_metrics import compute_all

        # 1. Build tiny dataset.
        train_path = _tiny_jsonl(tmp_path, n_examples=100)

        # 2. Train.
        model = ChordConditionedNGram(order=1, alpha=0.5, seed=42)
        model.fit(train_path)
        assert model.vocab_size() > 0

        # 3. Save model.
        model_path = tmp_path / "model.pkl"
        model.save(model_path)

        # 4. Infer.
        out_path = tmp_path / "result.mid"
        melody_bars = generate_midi(
            chord_progression=["Am", "Am", "Em", "Em", "Am", "Am", "Dm", "Dm"],
            model_path=model_path,
            out_path=out_path,
            tempo_bpm=100.0,
            seed=42,
        )

        assert out_path.exists()
        assert len(melody_bars) == 8

        # 5. Evaluate.
        flat_events = [ev for bar in melody_bars for ev in bar]
        metrics = compute_all(flat_events, ppqn=480, bars=8)
        assert 0.0 <= metrics["in_scale_rate"] <= 1.0
        assert metrics["note_count"] >= 0
