import pytest

from dictados.domain.pitch import Pitch, MIN_MIDI, MAX_MIDI


def test_pitch_range_valid():
    assert Pitch.from_midi(MIN_MIDI).midi_number == MIN_MIDI
    assert Pitch.from_midi(MAX_MIDI).midi_number == MAX_MIDI


def test_pitch_range_invalid():
    with pytest.raises(ValueError):
        Pitch.from_midi(MIN_MIDI - 1)
    with pytest.raises(ValueError):
        Pitch.from_midi(MAX_MIDI + 1)
