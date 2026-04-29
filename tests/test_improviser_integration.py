"""Integration tests for the ImproEngine and full pipeline."""
import random
from pathlib import Path

import pytest
import mido

from dictados.improviser.engine import ImproEngine
from dictados.improviser.theory import parse_chord_name, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI
from dictados.improviser.main import generate_improvisation
from dictados.improviser.text_parser import parse_text
from dictados.improviser.chord_track import build_chord_track
from dictados.improviser.melody_builder import build_melody_phrase

_PPQN = 480


class TestImproEngine:
    def test_output_length_matches_chords(self):
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "E"]]
        engine = ImproEngine(ppqn=_PPQN, seed=0)
        result = engine.improvise(chords)
        assert len(result) == len(chords)

    def test_each_measure_fills_correctly(self):
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "G7"]]
        engine = ImproEngine(ppqn=_PPQN, seed=42)
        result = engine.improvise(chords)
        measure_ticks = 4 * _PPQN
        for i, measure_notes in enumerate(result):
            total = sum(d for _, d in measure_notes)
            assert total == measure_ticks, f"Measure {i} total={total}"

    def test_notes_in_midi_range(self):
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "G7"]]
        engine = ImproEngine(ppqn=_PPQN, seed=7)
        result = engine.improvise(chords)
        for measure_notes in result:
            for midi, _dur in measure_notes:
                assert IMPRO_MIN_MIDI <= midi <= IMPRO_MAX_MIDI

    def test_deterministic_with_seed(self):
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "E"]]
        engine_a = ImproEngine(ppqn=_PPQN, seed=99)
        engine_b = ImproEngine(ppqn=_PPQN, seed=99)
        assert engine_a.improvise(chords) == engine_b.improvise(chords)

    def test_non_deterministic_without_seed(self):
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "E"]] * 4
        engine_a = ImproEngine(ppqn=_PPQN, seed=None)
        engine_b = ImproEngine(ppqn=_PPQN, seed=None)
        # Very unlikely to be equal by chance.
        assert engine_a.improvise(chords) != engine_b.improvise(chords)


class TestChordTrack:
    def test_measure_count_matches_chords(self):
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "E"]]
        phrase = build_chord_track(chords, ppqn=_PPQN)
        assert len(phrase.measures) == 4

    def test_each_measure_has_multiple_notes(self):
        chords = [parse_chord_name("Am")]
        phrase = build_chord_track(chords, ppqn=_PPQN)
        # Am triad has at least 3 notes.
        assert len(phrase.measures[0].notes) >= 3

    def test_chord_notes_fill_measure(self):
        chords = [parse_chord_name("C")]
        phrase = build_chord_track(chords, ppqn=_PPQN)
        measure = phrase.measures[0]
        measure_ticks = 4 * _PPQN
        for note in measure.notes:
            assert note.duration_ticks == measure_ticks


class TestFullPipeline:
    def test_generates_two_track_midi(self, tmp_path):
        out = tmp_path / "test_output.mid"
        chords = [parse_chord_name(n) for n in ["Am", "C", "Dm", "E"]]
        result = generate_improvisation(
            chords=chords,
            tempo_bpm=120,
            ppqn=_PPQN,
            seed=1,
            output_path=out,
        )
        assert result == out
        assert out.exists()

        # Verify the MIDI file structure.
        midi = mido.MidiFile(str(out))
        # Should have: 1 metadata track + 2 note tracks = 3 tracks total.
        assert len(midi.tracks) == 3

    def test_text_to_midi_pipeline(self, tmp_path):
        out = tmp_path / "text_pipeline.mid"
        prog = parse_text("2 ruedas de Am C Dm E, 120bpm")
        chords = prog.all_chords
        result = generate_improvisation(
            chords=chords,
            tempo_bpm=prog.tempo_bpm,
            ppqn=480,
            seed=42,
            output_path=out,
        )
        assert out.exists()
        midi = mido.MidiFile(str(out))
        # Verify two note tracks.
        note_tracks = [t for t in midi.tracks if any(not m.is_meta for m in t)]
        assert len(note_tracks) == 2
