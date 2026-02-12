from dictados.domain.scale import Scale
from dictados.domain.chord import ChordQuality


def test_scale_from_string_major():
    scale = Scale.from_string("C")
    assert scale.tonic_pc == 0


def test_scale_from_string_minor():
    scale = Scale.from_string("Am")
    assert scale.tonic_pc == 9


def test_scale_degree_pitch_class_major():
    scale = Scale.from_string("C")
    assert scale.degree_pitch_class(1) == 0
    assert scale.degree_pitch_class(2) == 2
    assert scale.degree_pitch_class(6) == 9


def test_scale_chord_from_degree():
    scale = Scale.from_string("C")
    chord = scale.chord_from_degree(1, ChordQuality.MAJOR)
    assert chord.root.pitch_class == 0
