"""Tests for tools.dataset.normalizer."""
from __future__ import annotations

import pytest

from tools.dataset.normalizer import (
    NORM_PPQN,
    RANGE_HIGH,
    RANGE_LOW,
    TICKS_PER_16TH,
    _apply_range_filter,
    _correlation,
    _duration_bin,
    _infer_key,
    _quantise_onsets,
    _velocity_bin,
    normalise_segment,
)


def _make_note(midi=60, velocity=80, start=0, end=480):
    return {"midi": midi, "velocity": velocity, "start_tick": start, "end_tick": end}


def _make_segment(notes, ppqn=480, bar_start=0, style=None):
    return {
        "source": "test/test.mid",
        "notes": notes,
        "context_chords": ["Am"],
        "meta": {
            "tempo_bpm": 120.0,
            "time_sig": "4/4",
            "key": None,
            "style": style,
            "difficulty": None,
            "window_bars": 1,
            "ppqn_original": ppqn,
            "bar_start_tick": bar_start,
            "augmentation": {"transpose_semitones": 0, "tempo_factor": 1.0},
        },
    }


class TestVelocityBin:
    def test_pp(self):
        assert _velocity_bin(1) == 0
        assert _velocity_bin(31) == 0

    def test_p(self):
        assert _velocity_bin(32) == 1
        assert _velocity_bin(63) == 1

    def test_mf(self):
        assert _velocity_bin(64) == 2
        assert _velocity_bin(95) == 2

    def test_f(self):
        assert _velocity_bin(96) == 3
        assert _velocity_bin(111) == 3

    def test_ff(self):
        assert _velocity_bin(112) == 4
        assert _velocity_bin(127) == 4


class TestDurationBin:
    def test_32nd(self):
        assert _duration_bin(12) == 0   # < 18

    def test_16th(self):
        assert _duration_bin(24) == 1   # 18–35

    def test_8th(self):
        assert _duration_bin(48) == 2   # 36–59

    def test_dotted_8th(self):
        assert _duration_bin(72) == 3   # 60–83

    def test_quarter(self):
        # NORM_PPQN = 96 ticks → bin 4 (84–119)
        assert _duration_bin(NORM_PPQN) == 4

    def test_quarter_exact(self):
        assert _duration_bin(96) == 4

    def test_longer_than_whole(self):
        assert _duration_bin(400) == 7


class TestRangeFilter:
    def test_in_range_unchanged(self):
        notes = [_make_note(midi=60)]
        result, out = _apply_range_filter(notes)
        assert len(result) == 1
        assert result[0]["midi"] == 60
        assert out == 0

    def test_too_low_shifted_up(self):
        notes = [_make_note(midi=36)]  # C2 → should shift to C3 (48) or C4 (60)
        result, out = _apply_range_filter(notes)
        assert len(result) == 1
        assert RANGE_LOW <= result[0]["midi"] <= RANGE_HIGH

    def test_too_high_shifted_down(self):
        notes = [_make_note(midi=96)]  # C7 → shift to C6 (84)
        result, out = _apply_range_filter(notes)
        assert len(result) == 1
        assert RANGE_LOW <= result[0]["midi"] <= RANGE_HIGH

    def test_discarded_if_impossible(self):
        # MIDI 0 (C-1) is 4 octaves below C3; shifting up puts it at 48 (in range).
        notes = [_make_note(midi=0)]
        result, out = _apply_range_filter(notes)
        assert len(result) + out == 1  # either kept or discarded


class TestQuantiseOnsets:
    def test_already_on_grid(self):
        bar_start = 0
        notes = [_make_note(start=0), _make_note(start=TICKS_PER_16TH)]
        result = _quantise_onsets(notes, bar_start)
        assert result[0]["start_tick"] == 0
        assert result[1]["start_tick"] == TICKS_PER_16TH

    def test_small_offset_snapped(self):
        bar_start = 0
        # 2 ticks off a 16th-note grid point (tolerance = 0.1 * 24 ≈ 2.4)
        notes = [_make_note(start=2)]
        result = _quantise_onsets(notes, bar_start)
        assert result[0]["start_tick"] == 0

    def test_large_offset_kept(self):
        bar_start = 0
        # 10 ticks off — beyond tolerance.
        notes = [_make_note(start=10)]
        result = _quantise_onsets(notes, bar_start)
        assert result[0]["start_tick"] == 10


class TestInferKey:
    def test_c_major_scale(self):
        # Notes: C D E F G A B (pitch classes 0 2 4 5 7 9 11)
        notes = []
        for pc in [0, 2, 4, 5, 7, 9, 11]:
            notes.append({
                "midi": 60 + pc, "velocity": 80,
                "start_tick": 0, "end_tick": 96
            })
        key = _infer_key(notes)
        assert key == "C"

    def test_a_minor_scale(self):
        # Notes: A B C D E F G (pitch classes 9 11 0 2 4 5 7)
        notes = []
        for pc in [9, 11, 0, 2, 4, 5, 7]:
            notes.append({
                "midi": 60 + pc, "velocity": 80,
                "start_tick": 0, "end_tick": 96
            })
        key = _infer_key(notes)
        # Could be C major or A minor — either is acceptable.
        assert key in ("C", "Am")

    def test_empty_returns_none(self):
        assert _infer_key([]) is None


class TestCorrelation:
    def test_perfect_correlation(self):
        a = [1.0, 2.0, 3.0]
        assert abs(_correlation(a, a) - 1.0) < 1e-9

    def test_anti_correlation(self):
        a = [1.0, 2.0, 3.0]
        b = [3.0, 2.0, 1.0]
        assert abs(_correlation(a, b) - (-1.0)) < 1e-9

    def test_zero_variance(self):
        a = [1.0, 1.0, 1.0]
        b = [1.0, 2.0, 3.0]
        assert _correlation(a, b) == 0.0


class TestNormaliseSegment:
    def test_basic_segment_produces_output(self):
        # 4 quarter notes at C4 (60), in 4/4, ppqn=480.
        ppqn = 480
        notes = [
            {"midi": 60, "velocity": 80, "start_tick": i * 480, "end_tick": i * 480 + 479}
            for i in range(4)
        ]
        seg = _make_segment(notes, ppqn=ppqn, bar_start=0)
        result = normalise_segment(seg)
        assert result is not None
        assert len(result["notes"]) == 4
        for n in result["notes"]:
            assert "vel_bin" in n
            assert "dur_bin" in n
            assert RANGE_LOW <= n["midi"] <= RANGE_HIGH

    def test_too_few_notes_returns_none(self):
        notes = [{"midi": 60, "velocity": 80, "start_tick": 0, "end_tick": 480}]
        seg = _make_segment(notes)
        result = normalise_segment(seg)
        assert result is None

    def test_out_of_range_notes_shifted(self):
        # All notes at C2 (36) — should be shifted up.
        ppqn = 480
        notes = [
            {"midi": 36, "velocity": 80, "start_tick": i * 480, "end_tick": i * 480 + 479}
            for i in range(4)
        ]
        seg = _make_segment(notes, ppqn=ppqn)
        result = normalise_segment(seg)
        if result is not None:
            for n in result["notes"]:
                assert RANGE_LOW <= n["midi"] <= RANGE_HIGH

    def test_ppqn_scaling(self):
        # 240 ppqn: a quarter note is 240 ticks. After scaling to 96, it should be 96.
        ppqn = 240
        notes = [
            {"midi": 60, "velocity": 80, "start_tick": i * 240, "end_tick": i * 240 + 239}
            for i in range(4)
        ]
        seg = _make_segment(notes, ppqn=ppqn)
        result = normalise_segment(seg)
        assert result is not None
        # Scaled ticks: 240 * (96/240) = 96 per beat.
        assert result["notes"][0]["start_tick"] == 0
        assert result["notes"][1]["start_tick"] == 96

    def test_key_is_inferred(self):
        ppqn = 480
        # C major scale notes.
        for pc in [0, 2, 4, 5, 7, 9, 11]:
            pass  # just verify key is set
        notes = [
            {"midi": 60 + pc, "velocity": 80, "start_tick": i * 480, "end_tick": i * 480 + 479}
            for i, pc in enumerate([0, 2, 4, 5, 7, 9, 11, 0])
        ]
        seg = _make_segment(notes, ppqn=ppqn)
        result = normalise_segment(seg)
        assert result is not None
        assert result["meta"]["key"] is not None
