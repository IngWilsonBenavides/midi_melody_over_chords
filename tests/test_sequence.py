import pytest

from dictados.domain.pitch import Pitch
from dictados.generators.sequence import SequenceApplicator


def test_sequence_apply_pattern():
    notes = [Pitch.from_midi(43), Pitch.from_midi(48), Pitch.from_midi(52), Pitch.from_midi(55)]
    result = SequenceApplicator.apply_pattern(notes, "4321")
    assert [p.midi_number for p in result] == [55, 52, 48, 43]


def test_sequence_invalid_pattern():
    notes = [Pitch.from_midi(43), Pitch.from_midi(48), Pitch.from_midi(52), Pitch.from_midi(55)]
    with pytest.raises(ValueError):
        SequenceApplicator.apply_pattern(notes, "1123")
