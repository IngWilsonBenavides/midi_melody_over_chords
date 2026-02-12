from dictados.generators.rhythm import RhythmEngine, Subdivision


def test_rhythm_quarter_ticks():
    engine = RhythmEngine(ppqn=480)
    assert engine.get_subdivision_ticks(Subdivision.QUARTER) == 480
