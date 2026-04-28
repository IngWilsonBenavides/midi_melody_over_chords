"""Tests for individual improvisation strategies."""
import random
import pytest
from dictados.improviser.theory import parse_chord_name, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI
from dictados.improviser.strategies.arpegio import ArpegioStrategy
from dictados.improviser.strategies.scale_walk import ScaleWalkStrategy
from dictados.improviser.strategies.lick import LickStrategy
from dictados.improviser.strategies.approach import ApproachToneStrategy
from dictados.improviser.strategies.motif import MotifStrategy
from dictados.improviser.strategies.weighted_random import WeightedRandomStrategy

_PPQN = 480
_MEASURE_TICKS = 4 * _PPQN  # 4/4

_CHORDS = [
    parse_chord_name("Am"),
    parse_chord_name("C"),
    parse_chord_name("Dm"),
    parse_chord_name("G7"),
]

_STRATEGIES = [
    ArpegioStrategy(),
    ScaleWalkStrategy(),
    LickStrategy(),
    ApproachToneStrategy(),
    WeightedRandomStrategy(),
]


def _rng(seed=0):
    return random.Random(seed)


class TestStrategiesFillMeasure:
    """Each strategy must produce notes that sum to exactly measure_ticks."""

    @pytest.mark.parametrize("strategy", _STRATEGIES)
    @pytest.mark.parametrize("chord", _CHORDS)
    def test_fills_measure(self, strategy, chord):
        notes = strategy.generate(
            chord=chord,
            measure_ticks=_MEASURE_TICKS,
            ppqn=_PPQN,
            prev_midi=60,
            rng=_rng(),
        )
        total = sum(d for _, d in notes)
        assert total == _MEASURE_TICKS, (
            f"{type(strategy).__name__} on {chord}: total={total}, expected={_MEASURE_TICKS}"
        )

    @pytest.mark.parametrize("strategy", _STRATEGIES)
    @pytest.mark.parametrize("chord", _CHORDS)
    def test_notes_in_range(self, strategy, chord):
        notes = strategy.generate(
            chord=chord,
            measure_ticks=_MEASURE_TICKS,
            ppqn=_PPQN,
            prev_midi=60,
            rng=_rng(),
        )
        for midi, _dur in notes:
            assert IMPRO_MIN_MIDI <= midi <= IMPRO_MAX_MIDI, (
                f"{type(strategy).__name__}: note {midi} out of range"
            )


class TestMotifStrategyWithContext:
    def test_fills_measure_with_context(self):
        strat = MotifStrategy()
        context = [60, 62, 64, 65, 67]
        notes = strat.generate(
            chord=parse_chord_name("C"),
            measure_ticks=_MEASURE_TICKS,
            ppqn=_PPQN,
            prev_midi=67,
            rng=_rng(7),
            context=context,
        )
        total = sum(d for _, d in notes)
        assert total == _MEASURE_TICKS

    def test_fills_measure_without_context(self):
        strat = MotifStrategy()
        notes = strat.generate(
            chord=parse_chord_name("Am"),
            measure_ticks=_MEASURE_TICKS,
            ppqn=_PPQN,
            prev_midi=60,
            rng=_rng(3),
            context=None,
        )
        assert sum(d for _, d in notes) == _MEASURE_TICKS


class TestArpegioLastNoteIsChordTone:
    def test_last_note_chord_tone(self):
        strat = ArpegioStrategy()
        chord = parse_chord_name("Am")
        notes = strat.generate(chord, _MEASURE_TICKS, _PPQN, 60, _rng(1))
        last_midi = notes[-1][0]
        chord_pcs = set(chord.get_chord_pitch_classes())
        assert last_midi % 12 in chord_pcs
