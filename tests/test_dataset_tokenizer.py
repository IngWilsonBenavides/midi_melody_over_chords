"""Tests for tools.dataset.tokenizer."""
from __future__ import annotations

import pytest

from tools.dataset.tokenizer import (
    _chord_root_pc,
    _compute_difficulty,
    _time_sig_to_bar_ticks,
    tokenise_segment,
)
from tools.dataset.normalizer import NORM_PPQN, TICKS_PER_16TH


def _make_norm_note(midi=60, vel_bin=2, dur_bin=4, start=0, end=96):
    return {
        "midi": midi,
        "velocity": 80,
        "vel_bin": vel_bin,
        "dur_bin": dur_bin,
        "start_tick": start,
        "end_tick": end,
    }


def _make_norm_segment(notes, chords=None, time_sig="4/4", window_bars=1, bar_start=0):
    return {
        "source": "test.mid",
        "notes": notes,
        "context_chords": chords or ["C"],
        "meta": {
            "tempo_bpm": 120.0,
            "time_sig": time_sig,
            "key": "C",
            "style": None,
            "difficulty": None,
            "window_bars": window_bars,
            "ppqn_original": 480,
            "ppqn_norm": NORM_PPQN,
            "bar_start_tick": bar_start,
            "augmentation": {"transpose_semitones": 0, "tempo_factor": 1.0},
        },
    }


class TestChordRootPc:
    def test_c_major(self):
        assert _chord_root_pc("C") == 0

    def test_a_minor(self):
        assert _chord_root_pc("Am") == 9

    def test_g7(self):
        assert _chord_root_pc("G7") == 7

    def test_db(self):
        assert _chord_root_pc("Db") == 1

    def test_unknown(self):
        assert _chord_root_pc("?") is None

    def test_empty(self):
        assert _chord_root_pc("") is None

    def test_f_sharp(self):
        assert _chord_root_pc("F#m") == 6


class TestTimeSigToBarTicks:
    def test_4_4(self):
        assert _time_sig_to_bar_ticks("4/4") == NORM_PPQN * 4

    def test_3_4(self):
        assert _time_sig_to_bar_ticks("3/4") == NORM_PPQN * 3

    def test_6_8(self):
        assert _time_sig_to_bar_ticks("6/8") == NORM_PPQN * 3  # 6 eighth notes

    def test_invalid_falls_back(self):
        assert _time_sig_to_bar_ticks("bad") == NORM_PPQN * 4


class TestComputeDifficulty:
    def test_empty_tokens(self):
        assert _compute_difficulty([], 0.0) == 0

    def test_simple_low_difficulty(self):
        tokens = [{"interval": 0}, {"interval": 2}, {"interval": 0}]
        d = _compute_difficulty(tokens, 3.0)
        assert d <= 2

    def test_high_density_raises_difficulty(self):
        tokens = [{"interval": i % 5} for i in range(20)]
        d = _compute_difficulty(tokens, 20.0)
        assert d >= 2

    def test_large_intervals_raise_difficulty(self):
        tokens = [{"interval": 10}, {"interval": -12}, {"interval": 8}]
        d = _compute_difficulty(tokens, 3.0)
        assert d >= 2

    def test_max_difficulty_capped_at_4(self):
        # Very dense, large intervals, chromatic.
        tokens = [{"interval": i - 12} for i in range(25)]
        d = _compute_difficulty(tokens, 25.0)
        assert d <= 4


class TestTokeniseSegment:
    def test_basic_tokenisation(self):
        notes = [_make_norm_note(midi=60 + i, start=i * TICKS_PER_16TH, end=i * TICKS_PER_16TH + TICKS_PER_16TH)
                 for i in range(4)]
        seg = _make_norm_segment(notes, chords=["C"], bar_start=0)
        result = tokenise_segment(seg)
        assert result is not None
        assert len(result["melody"]) == 4
        for tok in result["melody"]:
            assert "interval" in tok
            assert "dur_bin" in tok
            assert "vel_bin" in tok
            assert "pos_16th" in tok

    def test_interval_is_root_relative(self):
        # C4 (60) over C chord (root=0, pc=0) → interval should be 0.
        notes = [_make_norm_note(midi=60, start=0, end=96)]  # single note
        # Need at least 2 notes for normalise_segment but tokeniser is called after.
        notes.append(_make_norm_note(midi=64, start=96, end=192))
        seg = _make_norm_segment(notes, chords=["C"], bar_start=0)
        result = tokenise_segment(seg)
        assert result is not None
        # First note: C4 over C chord → interval 0
        assert result["melody"][0]["interval"] == 0

    def test_interval_e_over_c(self):
        # E4 (64) over C chord: pitch class 4, root 0 → interval +4
        notes = [_make_norm_note(midi=64, start=0, end=96),
                 _make_norm_note(midi=60, start=96, end=192)]
        seg = _make_norm_segment(notes, chords=["C"], bar_start=0)
        result = tokenise_segment(seg)
        assert result is not None
        assert result["melody"][0]["interval"] == 4

    def test_pos_16th_correct(self):
        # Note at tick 48 = 2 * TICKS_PER_16TH → pos_16th = 2
        notes = [_make_norm_note(start=0, end=48),
                 _make_norm_note(start=48, end=96)]
        seg = _make_norm_segment(notes, chords=["C"], bar_start=0)
        result = tokenise_segment(seg)
        assert result is not None
        assert result["melody"][0]["pos_16th"] == 0
        assert result["melody"][1]["pos_16th"] == 2

    def test_no_notes_returns_none(self):
        seg = _make_norm_segment([], chords=["C"])
        result = tokenise_segment(seg)
        assert result is None

    def test_difficulty_set(self):
        notes = [_make_norm_note(start=i * 24, end=i * 24 + 24) for i in range(8)]
        seg = _make_norm_segment(notes, chords=["Am"], bar_start=0)
        result = tokenise_segment(seg)
        assert result is not None
        assert result["meta"]["difficulty"] is not None
        assert 0 <= result["meta"]["difficulty"] <= 4

    def test_source_preserved(self):
        notes = [_make_norm_note(start=i * 48, end=i * 48 + 48) for i in range(4)]
        seg = _make_norm_segment(notes)
        seg["source"] = "custom/path.mid"
        result = tokenise_segment(seg)
        assert result is not None
        assert result["source"] == "custom/path.mid"

    def test_unknown_chord_uses_zero_interval(self):
        notes = [_make_norm_note(midi=60, start=0, end=96),
                 _make_norm_note(midi=64, start=96, end=192)]
        seg = _make_norm_segment(notes, chords=["?"], bar_start=0)
        result = tokenise_segment(seg)
        assert result is not None
        # When chord is unknown, interval defaults to 0.
        for tok in result["melody"]:
            assert tok["interval"] == 0
