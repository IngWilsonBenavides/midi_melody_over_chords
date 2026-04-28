from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.pitch import Pitch


def test_chord_triad_pitch_classes_major():
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR)
    assert chord.get_triad_pitch_classes() == [0, 4, 7]


def test_chord_triad_pitch_classes_minor():
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.MINOR)
    assert chord.get_triad_pitch_classes() == [0, 3, 7]


def test_chord_triad_pitch_classes_diminished():
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.DIMINISHED)
    assert chord.get_triad_pitch_classes() == [0, 3, 6]


def test_chord_pitch_classes_dom7():
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.DOM7)
    assert chord.get_chord_pitch_classes() == [0, 4, 7, 10]
