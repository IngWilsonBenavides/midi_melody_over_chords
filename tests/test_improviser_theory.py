"""Tests for the improviser theory module."""
import pytest
from dictados.domain.chord import Chord, ChordQuality
from dictados.improviser.theory import (
    parse_chord_name,
    chord_label,
    get_chord_tones_in_range,
    get_scale_tones_in_range,
    nearest_chord_tone,
    nearest_scale_tone,
    make_pitch,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)


class TestParseChordName:
    def test_major(self):
        c = parse_chord_name("C")
        assert c.quality == ChordQuality.MAJOR
        assert c.root.pitch_class == 0  # C

    def test_minor(self):
        c = parse_chord_name("Am")
        assert c.quality == ChordQuality.MINOR
        assert c.root.pitch_class == 9  # A

    def test_dominant_7(self):
        c = parse_chord_name("G7")
        assert c.quality == ChordQuality.DOM7
        assert c.root.pitch_class == 7  # G

    def test_major_7(self):
        c = parse_chord_name("Cmaj7")
        assert c.quality == ChordQuality.MAJ7

    def test_minor_7(self):
        c = parse_chord_name("Dm7")
        assert c.quality == ChordQuality.MIN7
        assert c.root.pitch_class == 2  # D

    def test_diminished(self):
        c = parse_chord_name("Bdim")
        assert c.quality == ChordQuality.DIMINISHED

    def test_sharp_root(self):
        c = parse_chord_name("F#m")
        assert c.quality == ChordQuality.MINOR
        assert c.root.pitch_class == 6  # F#

    def test_flat_root(self):
        c = parse_chord_name("Bb")
        assert c.quality == ChordQuality.MAJOR
        assert c.root.pitch_class == 10  # Bb

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_chord_name("")


class TestChordLabel:
    def test_minor_label(self):
        c = parse_chord_name("Am")
        assert chord_label(c) == "Am"

    def test_major_label(self):
        c = parse_chord_name("C")
        assert chord_label(c) == "C"

    def test_dom7_label(self):
        c = parse_chord_name("G7")
        assert chord_label(c) == "G7"


class TestGetChordTones:
    def test_c_major_has_tones_in_range(self):
        c = parse_chord_name("C")
        tones = get_chord_tones_in_range(c)
        # All should be C, E, or G pitch classes.
        chord_pcs = {0, 4, 7}
        assert all(m % 12 in chord_pcs for m in tones)
        assert all(IMPRO_MIN_MIDI <= m <= IMPRO_MAX_MIDI for m in tones)
        assert len(tones) > 0

    def test_am_minor_has_tones(self):
        c = parse_chord_name("Am")
        tones = get_chord_tones_in_range(c)
        chord_pcs = {9, 0, 4}  # A, C, E
        assert all(m % 12 in chord_pcs for m in tones)


class TestNearestChordTone:
    def test_returns_chord_tone(self):
        c = parse_chord_name("C")
        result = nearest_chord_tone(60, c)
        assert result % 12 in {0, 4, 7}

    def test_stays_in_range(self):
        c = parse_chord_name("Am")
        result = nearest_chord_tone(72, c)
        assert IMPRO_MIN_MIDI <= result <= IMPRO_MAX_MIDI


class TestMakePitch:
    def test_extended_range(self):
        # Should not raise even for notes above 81
        p = make_pitch(84)  # C6
        assert p.midi_number == 84

    def test_impro_range_bounds(self):
        p_low = make_pitch(IMPRO_MIN_MIDI)
        p_high = make_pitch(IMPRO_MAX_MIDI)
        assert p_low.midi_number == 48
        assert p_high.midi_number == 84
