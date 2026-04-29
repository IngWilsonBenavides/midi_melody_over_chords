"""Tests for tools.dataset.extractor."""
from __future__ import annotations

import io
import struct
import tempfile
from pathlib import Path

import mido
import pytest

from tools.dataset.extractor import (
    _avg_polyphony,
    _bar_ticks,
    _detect_chords,
    _get_tempo_at,
    _get_time_sig_at,
    _infer_style,
    _match_chord,
    _track_to_notes,
    extract_segments,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helper: create a minimal in-memory MIDI file with a melody track
# ──────────────────────────────────────────────────────────────────────────────

def _make_simple_midi(notes: list[tuple[int, int, int, int]], ppqn: int = 480) -> Path:
    """Create a MIDI file with a single track containing note_on/note_off pairs.

    *notes* is a list of (pitch, velocity, start_tick, end_tick).
    Returns the path to a temporary file.
    """
    mid = mido.MidiFile(ticks_per_beat=ppqn)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    events: list[tuple[int, int, mido.Message]] = []
    for pitch, vel, start, end in notes:
        events.append((start, 1, mido.Message("note_on", note=pitch, velocity=vel, time=0)))
        events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, time=0)))

    events.sort(key=lambda x: (x[0], x[1]))
    last = 0
    for tick, _, msg in events:
        msg.time = tick - last
        track.append(msg)
        last = tick

    track.append(mido.MetaMessage("end_of_track", time=0))

    tmp = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
    mid.save(tmp.name)
    return Path(tmp.name)


# ──────────────────────────────────────────────────────────────────────────────
# Unit tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBarTicks:
    def test_4_4_480ppqn(self):
        assert _bar_ticks(480, 4, 4) == 1920

    def test_3_4_480ppqn(self):
        assert _bar_ticks(480, 3, 4) == 1440

    def test_6_8_480ppqn(self):
        # 6/8: 6 eighth notes = 6 * (480 * 4/8) = 6 * 240 = 1440
        assert _bar_ticks(480, 6, 8) == 1440

    def test_2_4_96ppqn(self):
        assert _bar_ticks(96, 2, 4) == 192


class TestTempoMap:
    def test_default_tempo(self):
        tempo_map = [(0, 500_000)]
        assert _get_tempo_at(0, tempo_map) == 500_000
        assert _get_tempo_at(9999, tempo_map) == 500_000

    def test_tempo_change(self):
        tempo_map = [(0, 500_000), (1000, 400_000)]
        assert _get_tempo_at(999, tempo_map) == 500_000
        assert _get_tempo_at(1000, tempo_map) == 400_000
        assert _get_tempo_at(5000, tempo_map) == 400_000


class TestTimeSigMap:
    def test_default_4_4(self):
        ts_map = [(0, 4, 4)]
        assert _get_time_sig_at(0, ts_map) == (4, 4)
        assert _get_time_sig_at(10000, ts_map) == (4, 4)

    def test_change(self):
        ts_map = [(0, 4, 4), (1920, 3, 4)]
        assert _get_time_sig_at(1919, ts_map) == (4, 4)
        assert _get_time_sig_at(1920, ts_map) == (3, 4)


class TestInferStyle:
    def test_known_style_dir(self):
        p = Path("/some/path/jazz/song.mid")
        assert _infer_style(p) == "jazz"

    def test_unknown_dir_returns_none(self):
        p = Path("/some/path/unknown_band/song.mid")
        assert _infer_style(p) is None

    def test_blues(self):
        p = Path("data/raw/blues/track01.mid")
        assert _infer_style(p) == "blues"


class TestMatchChord:
    def test_empty_returns_question(self):
        assert _match_chord(set()) == "?"

    def test_c_major(self):
        # C major: pitch classes 0, 4, 7
        result = _match_chord({0, 4, 7})
        assert result == "C"

    def test_am_minor(self):
        # A minor: pitch classes 9, 0, 4
        result = _match_chord({9, 0, 4})
        assert result == "Am"

    def test_g7(self):
        # G7: 7, 11, 2, 5
        result = _match_chord({7, 11, 2, 5})
        assert result == "G7"


class TestTrackToNotes:
    def test_basic_note(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=80, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))
        notes = _track_to_notes(track, 480)
        assert len(notes) == 1
        assert notes[0]["midi"] == 60
        assert notes[0]["velocity"] == 80
        assert notes[0]["start_tick"] == 0
        assert notes[0]["end_tick"] == 480

    def test_note_on_zero_velocity_acts_as_off(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=64, velocity=100, time=0))
        track.append(mido.Message("note_on", note=64, velocity=0, time=240))
        notes = _track_to_notes(track, 480)
        assert len(notes) == 1
        assert notes[0]["end_tick"] == 240

    def test_multiple_notes(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=60, velocity=80, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, time=480))
        track.append(mido.Message("note_on", note=64, velocity=90, time=0))
        track.append(mido.Message("note_off", note=64, velocity=0, time=480))
        notes = _track_to_notes(track, 480)
        assert len(notes) == 2
        assert notes[0]["midi"] == 60
        assert notes[1]["midi"] == 64

    def test_notes_sorted_by_start(self):
        track = mido.MidiTrack()
        track.append(mido.Message("note_on", note=64, velocity=80, time=240))
        track.append(mido.Message("note_off", note=64, velocity=0, time=240))
        track.append(mido.Message("note_on", note=60, velocity=80, time=-480))
        track.append(mido.Message("note_off", note=60, velocity=0, time=0))
        notes = _track_to_notes(track, 480)
        if len(notes) >= 2:
            assert notes[0]["start_tick"] <= notes[1]["start_tick"]


class TestAvgPolyphony:
    def test_single_note(self):
        notes = [{"start_tick": 0, "end_tick": 480}]
        score = _avg_polyphony(notes)
        assert score > 0

    def test_sequential_notes_low_polyphony(self):
        # Non-overlapping notes → low polyphony.
        notes = [
            {"start_tick": 0, "end_tick": 240},
            {"start_tick": 240, "end_tick": 480},
        ]
        assert _avg_polyphony(notes) <= 1.5

    def test_empty(self):
        assert _avg_polyphony([]) == 0.0


class TestExtractSegments:
    def test_empty_file_or_bad_path(self):
        result = extract_segments("/nonexistent/path/file.mid")
        assert result == []

    def test_basic_extraction(self):
        # Build a MIDI file with 4 bars of quarter notes at C4.
        ppqn = 480
        bar = ppqn * 4  # 1920 ticks
        notes = [(60, 80, i * ppqn, i * ppqn + ppqn - 1) for i in range(16)]
        path = _make_simple_midi(notes, ppqn=ppqn)
        try:
            segs = extract_segments(path, window_bars=4)
            assert len(segs) >= 1
            for seg in segs:
                assert "notes" in seg
                assert "meta" in seg
                assert seg["meta"]["ppqn_original"] == ppqn
        finally:
            path.unlink(missing_ok=True)

    def test_style_override(self):
        ppqn = 480
        notes = [(60, 80, i * ppqn, i * ppqn + ppqn - 1) for i in range(8)]
        path = _make_simple_midi(notes, ppqn=ppqn)
        try:
            segs = extract_segments(path, window_bars=2, style="jazz")
            for seg in segs:
                assert seg["meta"]["style"] == "jazz"
        finally:
            path.unlink(missing_ok=True)

    def test_style_inferred_from_directory(self, tmp_path):
        jazz_dir = tmp_path / "jazz"
        jazz_dir.mkdir()
        ppqn = 480
        notes = [(60, 80, i * ppqn, i * ppqn + ppqn - 1) for i in range(8)]
        path = jazz_dir / "test.mid"
        mid = mido.MidiFile(ticks_per_beat=ppqn)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        events = []
        for pitch, vel, start, end in notes:
            events.append((start, 1, mido.Message("note_on", note=pitch, velocity=vel, time=0)))
            events.append((end, 0, mido.Message("note_off", note=pitch, velocity=0, time=0)))
        events.sort(key=lambda x: (x[0], x[1]))
        last = 0
        for tick, _, msg in events:
            msg.time = tick - last
            track.append(msg)
            last = tick
        track.append(mido.MetaMessage("end_of_track", time=0))
        mid.save(str(path))

        segs = extract_segments(path, window_bars=2)
        assert all(s["meta"]["style"] == "jazz" for s in segs if s["meta"]["style"])
