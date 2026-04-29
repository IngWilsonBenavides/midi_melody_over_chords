"""Tests for the voice leading module."""
import pytest
from dictados.improviser.voice_leading import (
    clamp_to_range,
    constrain_leap,
    apply_voice_leading,
    MAX_MELODIC_LEAP,
)
from dictados.improviser.theory import IMPRO_MIN_MIDI, IMPRO_MAX_MIDI


class TestClampToRange:
    def test_in_range(self):
        assert clamp_to_range(60) == 60

    def test_below_range(self):
        result = clamp_to_range(30)
        assert IMPRO_MIN_MIDI <= result <= IMPRO_MAX_MIDI

    def test_above_range(self):
        result = clamp_to_range(100)
        assert IMPRO_MIN_MIDI <= result <= IMPRO_MAX_MIDI


class TestConstrainLeap:
    def test_small_interval_unchanged(self):
        assert constrain_leap(60, 64) == 64

    def test_large_interval_reduced(self):
        result = constrain_leap(60, 85)
        assert abs(result - 60) <= MAX_MELODIC_LEAP

    def test_stays_in_range(self):
        result = constrain_leap(60, 20)
        assert IMPRO_MIN_MIDI <= result <= IMPRO_MAX_MIDI


class TestApplyVoiceLeading:
    def test_no_large_leaps(self):
        notes = [60, 84, 48, 72, 60]
        result = apply_voice_leading(notes)
        for i in range(1, len(result)):
            assert abs(result[i] - result[i - 1]) <= MAX_MELODIC_LEAP

    def test_all_in_range(self):
        notes = [60, 84, 48, 72, 60]
        result = apply_voice_leading(notes)
        assert all(IMPRO_MIN_MIDI <= m <= IMPRO_MAX_MIDI for m in result)

    def test_with_start_note(self):
        notes = [80, 65, 55]
        result = apply_voice_leading(notes, start=70)
        assert abs(result[0] - 70) <= MAX_MELODIC_LEAP
