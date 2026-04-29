"""MIDI extractor — imports monophonic MIDI files and extracts melodic segments.

Given a MIDI file the extractor:
1. Locates the most monophonic (lowest simultaneous-note count) track.
2. Detects tempo and time-signature changes.
3. Splits the track into windows of ``window_bars`` measures.
4. Optionally extracts chord context from a second (harmonic) track.
5. Returns a list of :class:`Segment` dicts ready for normalisation.

Usage::

    from tools.dataset.extractor import extract_segments

    segments = extract_segments("data/raw/jazz/example.mid", window_bars=4)
    for seg in segments:
        print(seg["notes"], seg["meta"])
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import mido

# Internal PPQN used after normalisation (24 ticks per 16th note).
NORM_PPQN: int = 96

# MIDI note range kept after range filtering (C3–C6).
RANGE_LOW: int = 48   # C3
RANGE_HIGH: int = 84  # C6

# Default window size in bars.
DEFAULT_WINDOW_BARS: int = 4


# ──────────────────────────────────────────────────────────────────────────────
# Public types
# ──────────────────────────────────────────────────────────────────────────────

# A raw note as read from MIDI before normalisation.
RawNote = dict[str, Any]  # {midi, velocity, start_tick, end_tick}

# A segment ready for normalisation.
Segment = dict[str, Any]  # {notes, context_chords, source, meta}


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def extract_segments(
    midi_path: str | Path,
    window_bars: int = DEFAULT_WINDOW_BARS,
    style: str | None = None,
) -> list[Segment]:
    """Extract windowed melodic segments from a MIDI file.

    Args:
        midi_path:    Path to the source `.mid` file.
        window_bars:  Number of bars per example window (default 4).
        style:        Optional style tag (overrides directory-name heuristic).

    Returns:
        List of :class:`Segment` dicts, one per window.
    """
    path = Path(midi_path)
    try:
        mid = mido.MidiFile(str(path))
    except Exception:
        return []

    ppqn = mid.ticks_per_beat or 480

    # Build a global tick→event timeline.
    tempo_map = _build_tempo_map(mid)
    time_sig_map = _build_time_sig_map(mid)

    # Infer style from parent directory name if not provided.
    if style is None:
        style = _infer_style(path)

    # Find the best melody track and an optional chord/harmonic track.
    melody_track_idx, chord_track_idx = _select_tracks(mid)
    if melody_track_idx is None:
        return []

    # Convert tracks to absolute-tick note lists.
    melody_notes = _track_to_notes(mid.tracks[melody_track_idx], ppqn)
    chord_notes = (
        _track_to_notes(mid.tracks[chord_track_idx], ppqn)
        if chord_track_idx is not None
        else []
    )

    if not melody_notes:
        return []

    # Split into bar-aligned windows.
    segments = _window_notes(
        melody_notes=melody_notes,
        chord_notes=chord_notes,
        ppqn=ppqn,
        tempo_map=tempo_map,
        time_sig_map=time_sig_map,
        window_bars=window_bars,
        source=str(path),
        style=style,
    )
    return segments


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_tempo_map(mid: mido.MidiFile) -> list[tuple[int, int]]:
    """Return list of (absolute_tick, tempo_us) sorted by tick."""
    tempo_events: list[tuple[int, int]] = [(0, 500_000)]  # default 120 BPM
    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "set_tempo":
                tempo_events.append((tick, msg.tempo))
    tempo_events.sort(key=lambda x: x[0])
    return tempo_events


def _build_time_sig_map(mid: mido.MidiFile) -> list[tuple[int, int, int]]:
    """Return list of (absolute_tick, numerator, denominator) sorted by tick."""
    ts_events: list[tuple[int, int, int]] = [(0, 4, 4)]  # default 4/4
    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "time_signature":
                ts_events.append((tick, msg.numerator, msg.denominator))
    ts_events.sort(key=lambda x: x[0])
    return ts_events


def _get_tempo_at(tick: int, tempo_map: list[tuple[int, int]]) -> int:
    """Return the active tempo (microseconds/beat) at the given tick."""
    tempo = tempo_map[0][1]
    for t, us in tempo_map:
        if t <= tick:
            tempo = us
        else:
            break
    return tempo


def _get_time_sig_at(
    tick: int, ts_map: list[tuple[int, int, int]]
) -> tuple[int, int]:
    """Return (numerator, denominator) active at the given tick."""
    num, den = ts_map[0][1], ts_map[0][2]
    for t, n, d in ts_map:
        if t <= tick:
            num, den = n, d
        else:
            break
    return num, den


def _bar_ticks(ppqn: int, numerator: int, denominator: int) -> int:
    """Return the number of MIDI ticks in one bar."""
    # One quarter note = ppqn ticks.
    # One beat of the time signature = ppqn * (4 / denominator) ticks.
    beat_ticks = ppqn * 4 // denominator
    return beat_ticks * numerator


def _select_tracks(
    mid: mido.MidiFile,
) -> tuple[int | None, int | None]:
    """Choose the melody track and an optional chord/bass track.

    The melody track is the one with the lowest average simultaneous note
    count (most monophonic).  Chord/bass track is the one with the highest
    average simultaneous note count among the remaining tracks.

    Returns:
        (melody_track_index, chord_track_index_or_None)
    """
    polyphony_scores: list[tuple[int, float]] = []

    for i, track in enumerate(mid.tracks):
        notes = _track_to_notes(track, mid.ticks_per_beat or 480)
        if not notes:
            continue
        score = _avg_polyphony(notes)
        polyphony_scores.append((i, score))

    if not polyphony_scores:
        return None, None

    polyphony_scores.sort(key=lambda x: x[1])
    melody_idx = polyphony_scores[0][0]

    chord_idx = None
    if len(polyphony_scores) > 1:
        # Pick the most polyphonic remaining track for chord context.
        chord_idx = max(polyphony_scores[1:], key=lambda x: x[1])[0]

    return melody_idx, chord_idx


def _avg_polyphony(notes: list[RawNote]) -> float:
    """Compute average number of simultaneously sounding notes."""
    if not notes:
        return 0.0
    events: list[tuple[int, int]] = []  # (tick, +1 or -1)
    for n in notes:
        events.append((n["start_tick"], 1))
        events.append((n["end_tick"], -1))
    events.sort()
    active = 0
    samples: list[int] = []
    for _, delta in events:
        active += delta
        samples.append(active)
    return sum(samples) / len(samples) if samples else 0.0


def _track_to_notes(track: mido.MidiTrack, ppqn: int) -> list[RawNote]:
    """Convert a MIDI track to a list of absolute-tick note dicts."""
    notes: list[RawNote] = []
    pending: dict[int, list[tuple[int, int]]] = {}  # pitch → [(start_tick, velocity)]
    tick = 0

    for msg in track:
        tick += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            pending.setdefault(msg.note, []).append((tick, msg.velocity))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            if msg.note in pending and pending[msg.note]:
                start_tick, velocity = pending[msg.note].pop(0)
                notes.append(
                    {
                        "midi": msg.note,
                        "velocity": velocity,
                        "start_tick": start_tick,
                        "end_tick": max(tick, start_tick + 1),
                    }
                )

    notes.sort(key=lambda n: n["start_tick"])
    return notes


def _infer_style(path: Path) -> str | None:
    """Infer style from the immediate parent directory name."""
    known_styles = {
        "jazz", "blues", "rock", "pop", "classical", "fusion",
        "reggae", "latin", "folk", "country", "funk", "soul",
        "metal", "electronic", "r&b", "rb",
    }
    parent = path.parent.name.lower()
    if parent in known_styles:
        return parent
    return None


def _window_notes(
    melody_notes: list[RawNote],
    chord_notes: list[RawNote],
    ppqn: int,
    tempo_map: list[tuple[int, int]],
    time_sig_map: list[tuple[int, int, int]],
    window_bars: int,
    source: str,
    style: str | None,
) -> list[Segment]:
    """Slice melody notes into bar-aligned windows and build Segment dicts."""
    if not melody_notes:
        return []

    first_tick = melody_notes[0]["start_tick"]
    last_tick = melody_notes[-1]["end_tick"]

    segments: list[Segment] = []
    bar_start = _quantise_to_bar_start(first_tick, ppqn, time_sig_map)

    while bar_start < last_tick:
        # Determine bar length at this position.
        num, den = _get_time_sig_at(bar_start, time_sig_map)
        single_bar = _bar_ticks(ppqn, num, den)
        window_end = bar_start + single_bar * window_bars

        # Collect notes in this window.
        window_melody = [
            n for n in melody_notes
            if n["start_tick"] >= bar_start and n["start_tick"] < window_end
        ]

        if len(window_melody) >= 2:
            tempo_us = _get_tempo_at(bar_start, tempo_map)
            tempo_bpm = round(60_000_000 / tempo_us, 2)
            context_chords = _detect_chords(chord_notes, bar_start, window_end, ppqn, num, den)

            segments.append(
                {
                    "source": source,
                    "notes": window_melody,
                    "context_chords": context_chords,
                    "meta": {
                        "tempo_bpm": tempo_bpm,
                        "time_sig": f"{num}/{den}",
                        "key": None,          # filled by normaliser
                        "style": style,
                        "difficulty": None,   # filled by tokeniser
                        "window_bars": window_bars,
                        "ppqn_original": ppqn,
                        "bar_start_tick": bar_start,
                        "augmentation": {"transpose_semitones": 0, "tempo_factor": 1.0},
                    },
                }
            )

        bar_start += single_bar

    return segments


def _quantise_to_bar_start(tick: int, ppqn: int, ts_map: list[tuple[int, int, int]]) -> int:
    """Round *tick* down to the nearest bar boundary."""
    num, den = _get_time_sig_at(tick, ts_map)
    bar = _bar_ticks(ppqn, num, den)
    if bar <= 0:
        return 0
    return (tick // bar) * bar


# ── Chord detection ───────────────────────────────────────────────────────────

_CHORD_TEMPLATES: dict[str, list[int]] = {
    # Major triads
    "C":  [0, 4, 7],   "C#": [1, 5, 8],  "Db": [1, 5, 8],
    "D":  [2, 6, 9],   "D#": [3, 7, 10], "Eb": [3, 7, 10],
    "E":  [4, 8, 11],  "F":  [5, 9, 0],  "F#": [6, 10, 1],
    "Gb": [6, 10, 1],  "G":  [7, 11, 2], "G#": [8, 0, 3],
    "Ab": [8, 0, 3],   "A":  [9, 1, 4],  "A#": [10, 2, 5],
    "Bb": [10, 2, 5],  "B":  [11, 3, 6],
    # Minor triads
    "Cm":  [0, 3, 7],  "C#m": [1, 4, 8],  "Dbm": [1, 4, 8],
    "Dm":  [2, 5, 9],  "D#m": [3, 6, 10], "Ebm": [3, 6, 10],
    "Em":  [4, 7, 11], "Fm":  [5, 8, 0],  "F#m": [6, 9, 1],
    "Gbm": [6, 9, 1],  "Gm":  [7, 10, 2], "G#m": [8, 11, 3],
    "Abm": [8, 11, 3], "Am":  [9, 0, 4],  "A#m": [10, 1, 5],
    "Bbm": [10, 1, 5], "Bm":  [11, 2, 6],
    # Dominant 7ths
    "C7":  [0, 4, 7, 10],  "D7":  [2, 6, 9, 0],  "E7":  [4, 8, 11, 2],
    "F7":  [5, 9, 0, 3],   "G7":  [7, 11, 2, 5],  "A7":  [9, 1, 4, 7],
    "B7":  [11, 3, 6, 9],
}


def _detect_chords(
    chord_notes: list[RawNote],
    start_tick: int,
    end_tick: int,
    ppqn: int,
    numerator: int,
    denominator: int,
) -> list[str]:
    """Detect chord symbols from a harmonic track, one per bar."""
    single_bar = _bar_ticks(ppqn, numerator, denominator)
    n_bars = max(1, math.ceil((end_tick - start_tick) / single_bar))
    result: list[str] = []

    for b in range(n_bars):
        bar_s = start_tick + b * single_bar
        bar_e = bar_s + single_bar
        pitches = {
            n["midi"] % 12
            for n in chord_notes
            if n["start_tick"] < bar_e and n["end_tick"] > bar_s
        }
        symbol = _match_chord(pitches)
        result.append(symbol)

    return result


def _match_chord(pitch_classes: set[int]) -> str:
    """Match a set of pitch classes to the best chord template."""
    if not pitch_classes:
        return "?"
    best_name = "?"
    best_score = -1
    for name, tones in _CHORD_TEMPLATES.items():
        template_set = set(tones)
        intersection = len(pitch_classes & template_set)
        union = len(pitch_classes | template_set)
        score = intersection / union if union else 0
        if score > best_score:
            best_score = score
            best_name = name
    return best_name
