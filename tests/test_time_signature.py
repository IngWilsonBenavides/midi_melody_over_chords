from dictados.domain.time_signature import TimeSignature


def test_time_signature_ticks():
    ts = TimeSignature(4, 4)
    assert ts.measure_ticks(480) == 1920
