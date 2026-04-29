"""Evaluation metrics for generated melodies.

All metrics operate on a flat list of ``(midi_pitch | None, duration_ticks, velocity)``
events — the raw output of the inference pipeline.

Metrics
-------
ngram_rep_rate
    Fraction of consecutive 3-grams in the pitch sequence that are repeated
    (higher = more mechanical / repetitive).

pitch_range_semitones
    Max − min MIDI pitch.  0 if no notes.

large_leap_rate
    Fraction of consecutive note pairs with |interval| > 7 semitones.

rhythmic_density
    Mean number of distinct 16th-note onset positions used per bar
    (higher = more rhythmically varied).

in_scale_rate
    Fraction of note pitches that belong to A natural minor
    (A B C D E F G  →  pitch classes {9,11,0,2,4,5,7}).
    Returns 1.0 if there are no notes.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

# A natural minor pitch classes: A(9) B(11) C(0) D(2) E(4) F(5) G(7)
_AM_SCALE_PCS: frozenset[int] = frozenset({9, 11, 0, 2, 4, 5, 7})


Event = tuple[Optional[int], int, int]  # (midi_pitch|None, dur_ticks, velocity)


def _pitches(events: list[Event]) -> list[int]:
    return [m for m, _d, _v in events if m is not None]


def ngram_rep_rate(events: list[Event], n: int = 3) -> float:
    """Fraction of consecutive pitch n-grams that are repeated."""
    pitches = _pitches(events)
    if len(pitches) < n + 1:
        return 0.0
    grams = [tuple(pitches[i: i + n]) for i in range(len(pitches) - n + 1)]
    counts = Counter(grams)
    repeated = sum(c - 1 for c in counts.values() if c > 1)
    return repeated / max(len(grams), 1)


def pitch_range_semitones(events: list[Event]) -> int:
    pitches = _pitches(events)
    if not pitches:
        return 0
    return max(pitches) - min(pitches)


def large_leap_rate(events: list[Event], threshold: int = 7) -> float:
    pitches = _pitches(events)
    if len(pitches) < 2:
        return 0.0
    leaps = sum(1 for a, b in zip(pitches, pitches[1:]) if abs(b - a) > threshold)
    return leaps / (len(pitches) - 1)


def rhythmic_density(
    events: list[Event],
    ppqn: int = 480,
    bars: int = 8,
) -> float:
    """Mean distinct 16th-note positions per bar."""
    if not events or bars == 0:
        return 0.0
    bar_ticks = ppqn * 4
    sixteenth = ppqn // 4

    onset = 0
    per_bar: list[set[int]] = [set() for _ in range(bars)]
    for midi_pitch, dur_ticks, _vel in events:
        bar_idx = min(onset // bar_ticks, bars - 1)
        if midi_pitch is not None and sixteenth > 0:
            pos = (onset % bar_ticks) // sixteenth
            per_bar[bar_idx].add(pos)
        onset += dur_ticks

    counts = [len(s) for s in per_bar]
    return sum(counts) / bars


def in_scale_rate(events: list[Event], scale_pcs: frozenset[int] = _AM_SCALE_PCS) -> float:
    """Fraction of pitched notes whose pitch class is in *scale_pcs*."""
    pitches = _pitches(events)
    if not pitches:
        return 1.0
    in_scale = sum(1 for m in pitches if m % 12 in scale_pcs)
    return in_scale / len(pitches)


def compute_all(
    events: list[Event],
    ppqn: int = 480,
    bars: int = 8,
) -> dict[str, float]:
    """Return all metrics as a dict."""
    return {
        "ngram_rep_rate":       round(ngram_rep_rate(events), 4),
        "pitch_range_semitones": pitch_range_semitones(events),
        "large_leap_rate":       round(large_leap_rate(events), 4),
        "rhythmic_density":      round(rhythmic_density(events, ppqn, bars), 2),
        "in_scale_rate":         round(in_scale_rate(events), 4),
        "note_count":            len(_pitches(events)),
        "rest_count":            sum(1 for m, _, _ in events if m is None),
    }
