"""Tests for the phrase library module."""
import pytest
from dictados.domain.chord import ChordQuality
from dictados.improviser.phrase_library import (
    MINOR_LICKS,
    MAJOR_LICKS,
    DOMINANT_LICKS,
    UNIVERSAL_LICKS,
    get_licks_for_quality,
)


class TestLickDurations:
    """All licks must sum to exactly 4.0 beats."""

    @staticmethod
    def _check_licks(licks, label):
        for i, lick in enumerate(licks):
            total = sum(beats for _, beats in lick)
            assert total == pytest.approx(4.0, abs=1e-9), (
                f"{label} lick #{i} sums to {total} beats instead of 4.0"
            )

    def test_minor_licks(self):
        self._check_licks(MINOR_LICKS, "MINOR")

    def test_major_licks(self):
        self._check_licks(MAJOR_LICKS, "MAJOR")

    def test_dominant_licks(self):
        self._check_licks(DOMINANT_LICKS, "DOMINANT")

    def test_universal_licks(self):
        self._check_licks(UNIVERSAL_LICKS, "UNIVERSAL")


class TestGetLicksForQuality:
    def test_minor_returns_minor_and_universal(self):
        pool = get_licks_for_quality(ChordQuality.MINOR)
        # Must include all minor licks.
        for lick in MINOR_LICKS:
            assert lick in pool

    def test_major_returns_major_and_universal(self):
        pool = get_licks_for_quality(ChordQuality.MAJOR)
        for lick in MAJOR_LICKS:
            assert lick in pool

    def test_dom7_returns_dominant(self):
        pool = get_licks_for_quality(ChordQuality.DOM7)
        for lick in DOMINANT_LICKS:
            assert lick in pool

    def test_pool_not_empty(self):
        for quality in ChordQuality:
            assert len(get_licks_for_quality(quality)) > 0
