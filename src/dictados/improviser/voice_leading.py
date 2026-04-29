"""Voice-leading constraints for the melodic improviser.

Ensures consecutive notes don't leap more than a configurable interval and
provides helpers to keep notes within the allowed MIDI range.
"""
from __future__ import annotations

from dictados.improviser.theory import IMPRO_MAX_MIDI, IMPRO_MIN_MIDI


MAX_MELODIC_LEAP = 12  # semitones — maximum allowed jump between consecutive notes


def clamp_to_range(midi: int, low: int = IMPRO_MIN_MIDI, high: int = IMPRO_MAX_MIDI) -> int:
    """Shift *midi* by octaves until it falls inside [low, high]."""
    while midi < low:
        midi += 12
    while midi > high:
        midi -= 12
    # Final safety clamp (shouldn't normally be needed)
    return max(low, min(high, midi))


def constrain_leap(current: int, target: int, max_leap: int = MAX_MELODIC_LEAP) -> int:
    """Return a version of *target* reachable from *current* within *max_leap*.

    If |target - current| > max_leap the target is shifted by octaves toward
    *current* until it fits, then clamped to the valid MIDI range.
    """
    result = target
    while abs(result - current) > max_leap:
        if result > current:
            result -= 12
        else:
            result += 12
    return clamp_to_range(result)


def apply_voice_leading(
    notes: list[int],
    start: int | None = None,
    max_leap: int = MAX_MELODIC_LEAP,
) -> list[int]:
    """Apply voice-leading constraints to a sequence of MIDI note numbers.

    Adjusts each note so consecutive intervals respect *max_leap* and all
    notes stay inside the IMPRO range.

    Args:
        notes: Sequence of MIDI note numbers.
        start: Optional preceding note (for continuity with previous measure).
        max_leap: Maximum semitone jump allowed between consecutive notes.

    Returns:
        New list with adjusted MIDI numbers.
    """
    result: list[int] = []
    prev = start if start is not None else notes[0] if notes else 60

    for midi in notes:
        adjusted = constrain_leap(prev, midi, max_leap)
        result.append(adjusted)
        prev = adjusted

    return result
