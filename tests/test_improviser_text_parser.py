"""Tests for the text parser module."""
import pytest
from dictados.domain.chord import ChordQuality
from dictados.improviser.text_parser import parse_text


class TestParseText:
    def test_simple_progression(self):
        result = parse_text("Am C Dm E")
        assert len(result.chords) == 4
        assert result.chords[0].quality == ChordQuality.MINOR  # Am
        assert result.chords[1].quality == ChordQuality.MAJOR  # C
        assert result.chords[2].quality == ChordQuality.MINOR  # Dm
        assert result.chords[3].quality == ChordQuality.MAJOR  # E

    def test_compases_sets_rounds(self):
        result = parse_text("4 compases de Am C Dm E")
        # 4 compases / 4 chords = 1 round
        assert result.rounds == 1
        assert len(result.chords) == 4

    def test_ruedas_sets_rounds(self):
        result = parse_text("2 ruedas de Am C Dm E")
        assert result.rounds == 2
        assert len(result.chords) == 4

    def test_tempo_detection(self):
        result = parse_text("Am C Dm E, 130bpm")
        assert result.tempo_bpm == 130

    def test_style_detection(self):
        result = parse_text("Am C Dm E, swing")
        assert result.style == "swing"

    def test_default_tempo(self):
        result = parse_text("Am C Dm E")
        assert result.tempo_bpm == 120

    def test_all_chords_expanded(self):
        result = parse_text("2 ruedas de Am C Dm E")
        assert len(result.all_chords) == 8

    def test_g7_chord(self):
        result = parse_text("C Am F G7")
        g7 = result.chords[3]
        assert g7.quality == ChordQuality.DOM7
        assert g7.root.pitch_class == 7  # G

    def test_no_chords_raises(self):
        with pytest.raises(ValueError):
            parse_text("2 ruedas de nada aqui")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_text("")
