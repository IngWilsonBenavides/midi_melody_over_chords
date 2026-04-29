"""Tokeniser — converts normalised segments to (interval, dur_bin, vel_bin, pos_16th) tokens.

The melody is expressed relative to the root of each bar's chord, making
every example transposition-invariant.  Rests are encoded with
``interval = null``.

Usage::

    from tools.dataset.tokenizer import tokenise_segment

    example = tokenise_segment(norm_segment)
"""
from __future__ import annotations

from typing import Any

from tools.dataset.normalizer import NORM_PPQN, TICKS_PER_16TH, RANGE_LOW, RANGE_HIGH

# Maximum interval stored (semitones above/below chord root).
MAX_INTERVAL: int = 24

# Beats per bar assumed when computing pos_16th for non-4/4.
_TICKS_PER_BAR_DEFAULT: int = NORM_PPQN * 4  # 4/4


# ──────────────────────────────────────────────────────────────────────────────
# Chord root lookup
# ──────────────────────────────────────────────────────────────────────────────

_ROOT_PC: dict[str, int] = {
    "C": 0,  "C#": 1, "Db": 1, "D": 2,  "D#": 3, "Eb": 3,
    "E": 4,  "F": 5,  "F#": 6, "Gb": 6, "G": 7,  "G#": 8,
    "Ab": 8, "A": 9,  "A#": 10,"Bb": 10,"B": 11,
}


def _chord_root_pc(chord_symbol: str) -> int | None:
    """Return the pitch class (0–11) of the root of a chord symbol."""
    if not chord_symbol or chord_symbol == "?":
        return None
    # Try longest prefix match.
    for length in (3, 2, 1):
        prefix = chord_symbol[:length]
        if prefix in _ROOT_PC:
            return _ROOT_PC[prefix]
    return None


def _time_sig_to_bar_ticks(time_sig: str) -> int:
    """Convert '4/4' → number of NORM_PPQN ticks in one bar."""
    try:
        num, den = (int(x) for x in time_sig.split("/"))
        beat_ticks = NORM_PPQN * 4 // den
        return beat_ticks * num
    except Exception:
        return _TICKS_PER_BAR_DEFAULT


# ──────────────────────────────────────────────────────────────────────────────
# Difficulty heuristic
# ──────────────────────────────────────────────────────────────────────────────

def _compute_difficulty(tokens: list[dict[str, Any]], notes_per_bar: float) -> int:
    """Compute a 0–4 difficulty score from token statistics."""
    if not tokens:
        return 0

    intervals = [abs(t["interval"]) for t in tokens if t["interval"] is not None]
    if not intervals:
        return 0

    avg_interval = sum(intervals) / len(intervals)
    chromatic = sum(1 for i in intervals if i % 2 != 0) / len(intervals)

    score = 0
    if notes_per_bar > 6:
        score += 1
    if notes_per_bar > 10:
        score += 1
    if avg_interval > 3:
        score += 1
    if avg_interval > 6:
        score += 1
    if chromatic > 0.3:
        score += 1

    return min(score, 4)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def tokenise_segment(segment: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a normalised segment to a training example dict.

    Returns:
        A dict with ``context_chords``, ``melody`` (list of NoteToken dicts),
        and ``meta``; or ``None`` if the segment produces no usable tokens.
    """
    notes: list[dict[str, Any]] = segment["notes"]
    context_chords: list[str] = segment.get("context_chords") or []
    meta: dict[str, Any] = segment["meta"]

    bar_ticks = _time_sig_to_bar_ticks(meta.get("time_sig", "4/4"))
    bar_start = meta.get("bar_start_tick", 0)
    window_bars: int = meta.get("window_bars", 4)

    tokens: list[dict[str, Any]] = []

    for note in notes:
        onset_abs = note["start_tick"]
        # Which bar within the window (0-indexed)?
        bar_idx = min(
            (onset_abs - bar_start) // bar_ticks,
            window_bars - 1,
        )
        bar_idx = max(bar_idx, 0)

        # Chord root for this bar.
        chord_symbol = (
            context_chords[bar_idx] if bar_idx < len(context_chords) else "?"
        )
        root_pc = _chord_root_pc(chord_symbol)

        # Interval relative to chord root (None → treat as chromatic passing tone with interval 0).
        if root_pc is not None:
            note_pc = note["midi"] % 12
            interval = note_pc - root_pc
            # Normalise to [−6, +5] (nearest semitone distance).
            if interval > 6:
                interval -= 12
            elif interval < -6:
                interval += 12
        else:
            interval = 0

        interval = max(-MAX_INTERVAL, min(MAX_INTERVAL, interval))

        # pos_16th: position within the bar in 16th-note units.
        onset_in_bar = (onset_abs - bar_start) % bar_ticks
        pos_16th = onset_in_bar // TICKS_PER_16TH

        tokens.append(
            {
                "interval": interval,
                "dur_bin": note["dur_bin"],
                "vel_bin": note["vel_bin"],
                "pos_16th": int(pos_16th),
            }
        )

    if not tokens:
        return None

    notes_per_bar = len(tokens) / window_bars
    difficulty = _compute_difficulty(tokens, notes_per_bar)

    out_meta = dict(meta)
    out_meta["difficulty"] = difficulty

    return {
        "source": segment["source"],
        "context_chords": context_chords,
        "melody": tokens,
        "meta": out_meta,
    }
