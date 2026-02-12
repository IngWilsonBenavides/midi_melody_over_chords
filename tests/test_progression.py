from dictados.domain.chord import ChordQuality
from dictados.domain.scale import Scale
from dictados.generators.progression import ProgressionGenerator, parse_roman_numeral


def test_parse_roman_numeral():
    degree, quality = parse_roman_numeral("IV")
    assert degree == 4
    assert quality == ChordQuality.MAJOR

    degree, quality = parse_roman_numeral("vi")
    assert degree == 6
    assert quality == ChordQuality.MINOR


def test_expand_progression_groups():
    scale = Scale.from_string("C")
    gen = ProgressionGenerator()
    chords = gen.expand_progression(["I", "iv"], 2, scale)
    assert len(chords) == 4
    assert chords[0].quality == ChordQuality.MAJOR
    assert chords[1].quality == ChordQuality.MINOR
