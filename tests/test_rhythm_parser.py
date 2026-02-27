"""Tests for rhythm parser."""

import pytest

from dictados.generators.rhythm_parser import (
    rhythm_to_ticks,
    parse_rhythm_list,
    validate_rhythm_for_measure,
)


class TestRhythmToTicks:
    def test_quarter_note(self):
        assert rhythm_to_ticks("q", ppqn=480) == 480

    def test_eighth_note(self):
        assert rhythm_to_ticks("e", ppqn=480) == 240

    def test_half_note(self):
        assert rhythm_to_ticks("h", ppqn=480) == 960

    def test_whole_note(self):
        assert rhythm_to_ticks("w", ppqn=480) == 1920

    def test_dotted_quarter(self):
        assert rhythm_to_ticks("qd", ppqn=480) == 720

    def test_dotted_half(self):
        assert rhythm_to_ticks("hd", ppqn=480) == 1440

    def test_sixteenth_note(self):
        assert rhythm_to_ticks("s", ppqn=480) == 120

    def test_case_insensitive(self):
        assert rhythm_to_ticks("Q", ppqn=480) == 480
        assert rhythm_to_ticks("QD", ppqn=480) == 720

    def test_unknown_notation_raises(self):
        with pytest.raises(ValueError):
            rhythm_to_ticks("x", ppqn=480)


class TestParseRhythmList:
    def test_single_note(self):
        result = parse_rhythm_list(["q"], ppqn=480)
        assert result == [480]

    def test_bach_measure_1(self):
        # [q, e, e, e, e] should total 1920 ticks (4 beats)
        result = parse_rhythm_list(["q", "e", "e", "e", "e"], ppqn=480)
        assert result == [480, 240, 240, 240, 240]
        assert sum(result) == 1920

    def test_bach_measure_2(self):
        # [q, q, q] should total 1440 ticks (3 beats in 3/4)
        result = parse_rhythm_list(["q", "q", "q"], ppqn=480)
        assert result == [480, 480, 480]
        assert sum(result) == 1440


class TestValidateRhythmForMeasure:
    def test_valid_4_4_measure(self):
        # 4 quarter notes = 4 beats = valid 4/4
        assert validate_rhythm_for_measure(
            ["q", "q", "q", "q"],
            "4/4",
            ppqn=480
        )

    def test_valid_3_4_measure(self):
        # 3 quarter notes = 3 beats = valid 3/4
        assert validate_rhythm_for_measure(
            ["q", "q", "q"],
            "3/4",
            ppqn=480
        )

    def test_bach_line_1_measure_1(self):
        # [q, e, e, e, e] in 3/4 should be 4 beats (invalid)
        with pytest.raises(ValueError):
            validate_rhythm_for_measure(
                ["q", "e", "e", "e", "e"],
                "3/4",
                ppqn=480
            )

    def test_bach_line_1_measure_1_in_4_4(self):
        # [q, e, e, e, e] in 4/4 should be valid (4 beats)
        assert validate_rhythm_for_measure(
            ["q", "e", "e", "e", "e"],
            "4/4",
            ppqn=480
        )

    def test_invalid_measure_raises(self):
        # 2 quarter notes in 4/4 = invalid
        with pytest.raises(ValueError):
            validate_rhythm_for_measure(
                ["q", "q"],
                "4/4",
                ppqn=480
            )
