"""Tests for tools.dataset.augmentor."""
from __future__ import annotations

import pytest

from tools.dataset.augmentor import (
    _transpose_chord,
    augment_example,
)


def _make_example(chords=None, melody=None, tempo=120.0):
    return {
        "source": "test.mid",
        "context_chords": chords or ["Am", "C", "Dm", "G"],
        "melody": melody or [
            {"interval": 0, "dur_bin": 4, "vel_bin": 2, "pos_16th": 0},
            {"interval": 2, "dur_bin": 2, "vel_bin": 2, "pos_16th": 4},
            {"interval": 3, "dur_bin": 2, "vel_bin": 3, "pos_16th": 6},
        ],
        "meta": {
            "tempo_bpm": tempo,
            "time_sig": "4/4",
            "key": "Am",
            "style": "jazz",
            "difficulty": 1,
            "window_bars": 4,
            "ppqn_original": 480,
            "augmentation": {"transpose_semitones": 0, "tempo_factor": 1.0},
        },
    }


class TestTransposeChord:
    def test_c_up_2(self):
        assert _transpose_chord("C", 2) == "D"

    def test_g_up_5(self):
        assert _transpose_chord("G", 5) == "C"

    def test_am_up_3(self):
        assert _transpose_chord("Am", 3) == "Cm"

    def test_c7_down_2(self):
        result = _transpose_chord("C7", -2)
        assert result == "A#7"

    def test_unknown_chord_unchanged(self):
        assert _transpose_chord("?", 5) == "?"

    def test_empty_chord_unchanged(self):
        assert _transpose_chord("", 5) == ""

    def test_octave_shift_is_identity(self):
        assert _transpose_chord("C", 12) == "C"

    def test_g7_up_2(self):
        result = _transpose_chord("G7", 2)
        assert result == "A7"


class TestAugmentExample:
    def test_returns_list(self):
        ex = _make_example()
        variants = augment_example(ex)
        assert isinstance(variants, list)
        assert len(variants) >= 1

    def test_identity_always_present(self):
        ex = _make_example()
        variants = augment_example(ex)
        identity = [
            v for v in variants
            if v["meta"]["augmentation"]["transpose_semitones"] == 0
            and v["meta"]["augmentation"]["tempo_factor"] == 1.0
        ]
        assert len(identity) >= 1

    def test_melody_tokens_unchanged(self):
        ex = _make_example()
        variants = augment_example(ex)
        # Melody intervals should be identical across all variants.
        original_intervals = [t["interval"] for t in ex["melody"]]
        for v in variants:
            assert [t["interval"] for t in v["melody"]] == original_intervals

    def test_chords_transposed(self):
        ex = _make_example(chords=["C"])
        variants = augment_example(ex)
        shifts_seen = set()
        for v in variants:
            shift = v["meta"]["augmentation"]["transpose_semitones"]
            shifts_seen.add(shift)
        # Multiple transpositions should be present.
        assert len(shifts_seen) > 1

    def test_tempo_jitter_applied(self):
        ex = _make_example(tempo=120.0)
        variants = augment_example(ex)
        tempos = {v["meta"]["tempo_bpm"] for v in variants}
        # Should have at least 2 different tempos (original + jittered).
        assert len(tempos) >= 2

    def test_no_leakage_between_variants(self):
        """Mutations to one variant must not affect another."""
        ex = _make_example()
        variants = augment_example(ex)
        if len(variants) >= 2:
            variants[0]["melody"][0]["interval"] = 99
            assert variants[1]["melody"][0]["interval"] != 99

    def test_augmentation_metadata_recorded(self):
        ex = _make_example()
        variants = augment_example(ex)
        for v in variants:
            aug = v["meta"]["augmentation"]
            assert "transpose_semitones" in aug
            assert "tempo_factor" in aug

    def test_all_12_keys_attempted(self):
        ex = _make_example(chords=["C"])
        variants = augment_example(ex)
        shifts = {v["meta"]["augmentation"]["transpose_semitones"] for v in variants}
        # At least several keys should be generated (some may be filtered by range).
        assert len(shifts) >= 6

    def test_source_preserved(self):
        ex = _make_example()
        variants = augment_example(ex)
        for v in variants:
            assert v["source"] == ex["source"]
