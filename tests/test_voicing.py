import pytest

from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.pitch import Pitch
from dictados.generators.voicing import VoicingEngine


def test_voicing_rotation_c_major():
    engine = VoicingEngine(Pitch.from_midi(41), Pitch.from_midi(81))
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR)

    v1 = [p.midi_number for p in engine.get_next_voicing(chord)]
    v2 = [p.midi_number for p in engine.get_next_voicing(chord)]
    v3 = [p.midi_number for p in engine.get_next_voicing(chord)]

    assert v1 == [43, 48, 52, 55]  # G1 C1 E1 G2
    assert v2 == [48, 52, 55, 60]  # C1 E1 G2 C2
    assert v3 == [52, 55, 60, 64]  # E1 G2 C2 E2


def test_voicing_rotation_am_dm_examples():
    engine = VoicingEngine(Pitch.from_midi(41), Pitch.from_midi(81))
    am = Chord(root=Pitch.from_midi(69), quality=ChordQuality.MINOR)
    dm = Chord(root=Pitch.from_midi(62), quality=ChordQuality.MINOR)

    v1 = [p.midi_number for p in engine.get_next_voicing(am)]
    v2 = [p.midi_number for p in engine.get_next_voicing(dm)]
    v3 = [p.midi_number for p in engine.get_next_voicing(am)]
    v4 = [p.midi_number for p in engine.get_next_voicing(dm)]

    assert v1 == [45, 48, 52, 57]  # A1 C1 E1 A2
    assert v2 == [41, 45, 50, 53]  # F1 A1 D1 F2
    assert v3 == [48, 52, 57, 60]  # C1 E1 A2 C2
    assert v4 == [45, 50, 53, 57]  # A1 D1 F2 A2


def test_voicing_exceeds_range():
    engine = VoicingEngine(Pitch.from_midi(41), Pitch.from_midi(50))
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR)
    with pytest.raises(ValueError):
        engine.get_next_voicing(chord)
