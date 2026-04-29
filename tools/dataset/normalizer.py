"""MIDI normaliser — re-quantises, range-filters, and bins notes.

Transforms a raw :class:`Segment` (output of :mod:`tools.dataset.extractor`)
into a normalised segment where:

- All ticks are scaled to ``NORM_PPQN = 96`` ticks per quarter note.
- Notes outside MIDI range 48–84 (C3–C6) are shifted by octaves or discarded.
- Raw MIDI velocities are binned into 5 levels (0–4).
- Onsets are snapped to the nearest 16th-note grid point (flexible ±10%).
- Durations are binned into 8 levels (0–7).
- Key is inferred via Krumhansl–Schmuckler profiles.

Usage::

    from tools.dataset.normalizer import normalise_segment

    norm = normalise_segment(raw_segment)
"""
from __future__ import annotations

from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

NORM_PPQN: int = 96        # ticks per quarter note after normalisation
TICKS_PER_16TH: int = NORM_PPQN // 4   # = 24

RANGE_LOW: int = 48   # C3
RANGE_HIGH: int = 84  # C6

# Maximum fraction of notes allowed outside range before discarding segment.
MAX_OUT_OF_RANGE_FRACTION: float = 0.20

# Flexible quantisation tolerance: snap if within this fraction of a 16th note.
FLEX_QUANT_TOLERANCE: float = 0.10

# ── Duration bin edges (in NORM_PPQN ticks, upper-exclusive) ─────────────────
# At NORM_PPQN=96: 32nd=12, 16th=24, 8th=48, dotted-8th=72,
#                  quarter=96, dotted-quarter=144, half=192
# bin 0 → 32nd    (< 18 ticks)
# bin 1 → 16th    (18–35)
# bin 2 → 8th     (36–59)
# bin 3 → dotted 8th (60–83)
# bin 4 → quarter   (84–119)
# bin 5 → dotted quarter (120–167)
# bin 6 → half       (168–287)
# bin 7 → whole / longer (≥ 288)
_DUR_EDGES: list[int] = [18, 36, 60, 84, 120, 168, 288]

# ── Velocity bin edges (upper-exclusive) ─────────────────────────────────────
# bin 0 = pp (1–31), bin 1 = p (32–63), bin 2 = mf (64–95),
# bin 3 = f (96–111), bin 4 = ff (112–127)
_VEL_EDGES: list[int] = [32, 64, 96, 112]

# ── Krumhansl–Schmuckler key profiles ────────────────────────────────────────
_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                  2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                  2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
               "F#", "G", "G#", "A", "A#", "B"]


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def normalise_segment(segment: dict[str, Any]) -> dict[str, Any] | None:
    """Normalise a raw segment.

    Returns a new segment dict with normalised notes, or ``None`` if the
    segment should be discarded (too few usable notes, too many out-of-range).
    """
    ppqn_orig: int = segment["meta"]["ppqn_original"]
    raw_notes: list[dict[str, Any]] = segment["notes"]

    # 1. Scale ticks to NORM_PPQN.
    scale = NORM_PPQN / ppqn_orig
    scaled = [
        {
            "midi": n["midi"],
            "velocity": n["velocity"],
            "start_tick": round(n["start_tick"] * scale),
            "end_tick": round(n["end_tick"] * scale),
        }
        for n in raw_notes
    ]

    # 2. Range filter — shift by octaves, discard if still out of range.
    in_range, out_count = _apply_range_filter(scaled)

    total = len(scaled)
    if total == 0:
        return None
    if out_count / total > MAX_OUT_OF_RANGE_FRACTION:
        return None
    if len(in_range) < 2:
        return None

    # 3. Quantise onsets to 16th-note grid (flexible ±10%).
    bar_start_norm = round(segment["meta"]["bar_start_tick"] * scale)
    quantised = _quantise_onsets(in_range, bar_start_norm)

    # 4. Bin velocities.
    for n in quantised:
        n["vel_bin"] = _velocity_bin(n["velocity"])

    # 5. Bin durations.
    for n in quantised:
        n["dur_bin"] = _duration_bin(n["end_tick"] - n["start_tick"])

    # 6. Infer key.
    key = _infer_key(quantised)

    # Build normalised segment.
    norm_meta = dict(segment["meta"])
    norm_meta["key"] = key
    norm_meta["ppqn_norm"] = NORM_PPQN

    return {
        "source": segment["source"],
        "notes": quantised,
        "context_chords": segment["context_chords"],
        "meta": norm_meta,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _apply_range_filter(
    notes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Shift notes by octaves to fit C3–C6; count those that couldn't fit."""
    result: list[dict[str, Any]] = []
    out_count = 0

    for n in notes:
        midi = n["midi"]
        # Shift up.
        while midi < RANGE_LOW:
            midi += 12
        # Shift down.
        while midi > RANGE_HIGH:
            midi -= 12
        # Still out of range → discard.
        if midi < RANGE_LOW or midi > RANGE_HIGH:
            out_count += 1
            continue
        result.append({**n, "midi": midi})

    return result, out_count


def _quantise_onsets(
    notes: list[dict[str, Any]],
    bar_start: int,
) -> list[dict[str, Any]]:
    """Snap note onsets to the nearest 16th-note grid, with ±10% tolerance."""
    result = []
    for n in notes:
        onset_rel = n["start_tick"] - bar_start
        # Nearest 16th.
        grid_step = TICKS_PER_16TH
        nearest = round(onset_rel / grid_step) * grid_step
        # Accept if within tolerance.
        tolerance = grid_step * FLEX_QUANT_TOLERANCE
        if abs(onset_rel - nearest) <= tolerance + 0.5:
            snapped = nearest
        else:
            snapped = onset_rel  # keep original if too far
        result.append({**n, "start_tick": bar_start + snapped})
    return result


def _velocity_bin(velocity: int) -> int:
    """Map raw MIDI velocity (1–127) to a bin index (0–4)."""
    for i, edge in enumerate(_VEL_EDGES):
        if velocity < edge:
            return i
    return len(_VEL_EDGES)  # bin 4 = ff


def _duration_bin(ticks: int) -> int:
    """Map a tick duration to a bin index (0–7)."""
    for i, edge in enumerate(_DUR_EDGES):
        if ticks < edge:
            return i
    return len(_DUR_EDGES)  # bin 7 = whole/longer


def _infer_key(notes: list[dict[str, Any]]) -> str | None:
    """Infer key using Krumhansl–Schmuckler pitch-class histogram."""
    if not notes:
        return None

    # Build pitch-class histogram.
    histogram = [0.0] * 12
    for n in notes:
        pc = n["midi"] % 12
        dur = n["end_tick"] - n["start_tick"]
        histogram[pc] += max(dur, 1)

    total = sum(histogram)
    if total == 0:
        return None
    histogram = [h / total for h in histogram]

    best_key = None
    best_score = float("-inf")

    for root in range(12):
        # Major
        rotated = histogram[root:] + histogram[:root]
        score = _correlation(rotated, _MAJOR_PROFILE)
        if score > best_score:
            best_score = score
            best_key = _NOTE_NAMES[root]

        # Minor
        score = _correlation(rotated, _MINOR_PROFILE)
        if score > best_score:
            best_score = score
            best_key = _NOTE_NAMES[root] + "m"

    return best_key


def _correlation(a: list[float], b: list[float]) -> float:
    """Pearson correlation between two equal-length lists."""
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    den_a = sum((x - mean_a) ** 2 for x in a) ** 0.5
    den_b = sum((y - mean_b) ** 2 for y in b) ** 0.5
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)
