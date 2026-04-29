"""Vocabulary helpers — bucketing, chord-quality parsing, dur_bin ↔ ticks.

These utilities are shared across the training and inference pipelines.
Everything is deterministic (no random state here).

Dataset token format (from tools/dataset/tokenizer.py):
    interval : int | None  — semitones from chord root; None = REST
    dur_bin  : int 0–7     — duration bucket (see normalizer.py _DUR_EDGES)
    vel_bin  : int 0–4     — velocity bucket
    pos_16th : int 0–15    — 16th-note position within the bar
"""
from __future__ import annotations

from typing import Optional

# ── Interval bucketing ────────────────────────────────────────────────────────
# Semitone range stored by tokeniser: −6 to +5 (nearest-semitone distance).
# We further bucket into steps of 2 to reduce state space for the Markov model.
# Buckets: REST (None), -6, -4, -2, 0, 2, 4, 6 → 8 pitch buckets + 1 REST = 9 states.

_BUCKET_STEP = 2
_BUCKET_MIN = -6
_BUCKET_MAX = 6


def bucket_interval(interval: Optional[int]) -> Optional[int]:
    """Quantise *interval* to the nearest even bucket (step=2), or None for REST."""
    if interval is None:
        return None
    # Round to nearest multiple of _BUCKET_STEP.
    bucket = round(interval / _BUCKET_STEP) * _BUCKET_STEP
    return max(_BUCKET_MIN, min(_BUCKET_MAX, bucket))


# ── Chord quality parsing ─────────────────────────────────────────────────────
# Map chord suffix → quality tag used as a Markov conditioning feature.
# Tags: "m" minor, "M" major, "7" dominant, "dim" diminished, "?" unknown.

def chord_quality_tag(chord_symbol: str) -> str:
    """Infer a quality tag from a chord symbol like 'Am', 'G7', 'Cmaj7'."""
    if not chord_symbol or chord_symbol == "?":
        return "?"
    # Strip root (1–2 chars).
    s = chord_symbol.strip()
    if len(s) >= 2 and s[1] in ("#", "b"):
        suffix = s[2:].lower()
    else:
        suffix = s[1:].lower()

    if suffix in ("m7", "min7", "-7"):
        return "m"
    if suffix in ("maj7", "Δ7", "Δ", "maj"):
        return "M"
    if suffix in ("7",):
        return "7"
    if suffix in ("dim", "°", "o", "dim7", "o7"):
        return "dim"
    if suffix in ("m", "min", "-"):
        return "m"
    if suffix == "":
        return "M"
    # Unknown → neutral fallback.
    return "?"


# ── Duration bin ↔ ticks ──────────────────────────────────────────────────────
# Mirrors tools/dataset/normalizer.py at NORM_PPQN=96.
# Representative tick counts (midpoint of each bin range):
#   bin 0 → 32nd      ≈ 12 ticks
#   bin 1 → 16th      ≈ 24 ticks
#   bin 2 → 8th       ≈ 48 ticks
#   bin 3 → dotted 8th ≈ 72 ticks
#   bin 4 → quarter    ≈ 96 ticks
#   bin 5 → dotted qtr ≈ 144 ticks
#   bin 6 → half       ≈ 192 ticks
#   bin 7 → whole      ≈ 384 ticks

NORM_PPQN: int = 96

_DUR_BIN_TICKS: list[int] = [12, 24, 48, 72, 96, 144, 192, 384]


def dur_bin_to_ticks(dur_bin: int, ppqn: int = 480) -> int:
    """Convert a duration bin (0–7) to absolute MIDI ticks at *ppqn*.

    Scales from NORM_PPQN=96 to the requested ppqn.
    """
    dur_bin = max(0, min(7, dur_bin))
    norm_ticks = _DUR_BIN_TICKS[dur_bin]
    return round(norm_ticks * ppqn / NORM_PPQN)


def ticks_to_dur_bin(ticks: int, ppqn: int = 480) -> int:
    """Map absolute MIDI ticks to the nearest duration bin."""
    norm_ticks = round(ticks * NORM_PPQN / ppqn)
    edges = [18, 36, 60, 84, 120, 168, 288]
    for i, edge in enumerate(edges):
        if norm_ticks < edge:
            return i
    return 7


# ── Velocity ──────────────────────────────────────────────────────────────────
# vel_bin 0–4 → representative MIDI velocities.
_VEL_BIN_VALUES: list[int] = [24, 48, 80, 104, 120]


def vel_bin_to_velocity(vel_bin: int) -> int:
    """Convert vel_bin (0–4) to a representative MIDI velocity."""
    vel_bin = max(0, min(4, vel_bin))
    return _VEL_BIN_VALUES[vel_bin]


# ── beat_group helper ─────────────────────────────────────────────────────────

def pos_16th_to_beat_group(pos_16th: int) -> int:
    """Convert a 0–15 16th-note position to a 0–3 quarter-note beat group."""
    return (pos_16th % 16) // 4
