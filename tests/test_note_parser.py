"""Tests for note parser."""

import pytest

from dictados.generators.note_parser import (
    parse_note_name,
    parse_notes_list,
)


class TestParseNoteName:
    def test_C_default_octave(self):
        result = parse_note_name("C")
        assert result["note_type"] == "normal"
        assert result["midi_number"] == 60  # C4

    def test_D_default_octave(self):
        result = parse_note_name("D")
        assert result["midi_number"] == 62  # D4

    def test_G_default_octave(self):
        result = parse_note_name("G")
        assert result["midi_number"] == 67  # G4

    def test_note_with_octave(self):
        result = parse_note_name("D4")
        assert result["midi_number"] == 62

    def test_note_with_octave_3(self):
        result = parse_note_name("G3")
        assert result["midi_number"] == 55

    def test_note_with_sharp(self):
        result = parse_note_name("C#")
        assert result["midi_number"] == 61

    def test_note_with_flat(self):
        result = parse_note_name("Db")
        assert result["midi_number"] == 61

    def test_case_insensitive(self):
        assert parse_note_name("c")["midi_number"] == 60
        assert parse_note_name("C")["midi_number"] == 60
        assert parse_note_name("c#")["midi_number"] == 61

    def test_rest_symbol_dash(self):
        result = parse_note_name("-")
        assert result["note_type"] == "rest"
        assert result["midi_number"] is None

    def test_rest_symbol_word(self):
        result = parse_note_name("rest")
        assert result["note_type"] == "rest"
        assert result["midi_number"] is None

    def test_ghost_note_symbol(self):
        result = parse_note_name("~")
        assert result["note_type"] == "ghost"
        assert result["midi_number"] is None

    def test_muted_note_symbol(self):
        result = parse_note_name("x")
        assert result["note_type"] == "muted"
        assert result["midi_number"] is None

    def test_invalid_note_raises(self):
        with pytest.raises(ValueError):
            parse_note_name("H")  # Not a valid note

    def test_invalid_octave_raises(self):
        with pytest.raises(ValueError):
            parse_note_name("C9999")  # Out of range


class TestParseNotesList:
    def test_single_note(self):
        result = parse_notes_list(["D"])
        assert len(result) == 1
        assert result[0]["midi_number"] == 62

    def test_bach_measure_1_notes(self):
        # [D, G, A, B, C] - should stay in octave 4 except C might go up
        result = parse_notes_list(["D", "G", "A", "B", "C"], default_octave=4)
        assert result[0]["midi_number"] == 62  # D4
        assert result[1]["midi_number"] == 67  # G4
        assert result[2]["midi_number"] == 69  # A4
        assert result[3]["midi_number"] == 71  # B4
        # C should still be 4 since it's higher in pitch than B within the octave
        assert result[4]["midi_number"] == 72  # C5 (inferred octave up)

    def test_with_rests(self):
        result = parse_notes_list(["D", "-", "G"])
        assert result[0]["midi_number"] == 62
        assert result[1]["midi_number"] is None
        assert result[1]["note_type"] == "rest"
        assert result[2]["midi_number"] == 67

    def test_with_special_notes(self):
        result = parse_notes_list(["D", "x", "G", "~"])
        assert result[0]["note_type"] == "normal"
        assert result[1]["note_type"] == "muted"
        assert result[2]["note_type"] == "normal"
        assert result[3]["note_type"] == "ghost"
