"""Phrase library — 20 melodic licks for the improviser.

Each lick is a list of ``(interval, beats)`` tuples where:
- ``interval`` is the offset in semitones from the chord root (can be negative
  or greater than 12 to span multiple octaves).
- ``beats`` is the duration in quarter-note beats (0.5 = eighth, 1.0 = quarter,
  2.0 = half).

Licks are grouped by the chord quality they work best over:
- ``MINOR_LICKS``   — over minor and min7 chords
- ``MAJOR_LICKS``   — over major and maj7 chords
- ``DOMINANT_LICKS``— over dominant-7th chords
- ``UNIVERSAL_LICKS``— work well over any chord quality

All licks sum to exactly **4 beats** (one 4/4 measure).
"""
from __future__ import annotations

from dictados.domain.chord import ChordQuality

# Type alias: (semitone interval from root, duration in beats)
Lick = list[tuple[int, float]]


# ─── Minor licks ──────────────────────────────────────────────────────────────
MINOR_LICKS: list[Lick] = [
    # 1 — Simple ascending minor triad, quarter notes
    [(0, 1.0), (3, 1.0), (7, 1.0), (12, 1.0)],

    # 2 — Minor bebop run (eighths)
    [(0, 0.5), (2, 0.5), (3, 0.5), (5, 0.5), (7, 0.5), (5, 0.5), (3, 0.5), (2, 0.5)],

    # 3 — Blues-flavored minor line (mix of quarters and eighths)
    [(0, 0.5), (3, 0.5), (5, 0.5), (6, 0.5), (7, 1.0), (10, 1.0)],

    # 4 — Descending minor run with leading tone
    [(12, 0.5), (10, 0.5), (8, 0.5), (7, 0.5), (5, 0.5), (3, 0.5), (2, 0.5), (0, 0.5)],

    # 5 — Minor swing phrase: root → 3rd → 5th → back
    [(0, 0.5), (3, 0.5), (7, 0.5), (10, 0.5), (7, 1.0), (3, 1.0)],

    # 6 — Pentatonic minor motif
    [(0, 0.5), (3, 0.5), (5, 1.0), (7, 0.5), (10, 0.5), (7, 1.0)],

    # 7 — Minor 3rd leap with scale fill
    [(7, 0.5), (5, 0.5), (3, 1.0), (2, 0.5), (0, 0.5), (3, 0.5), (5, 0.5)],
]

# ─── Major licks ──────────────────────────────────────────────────────────────
MAJOR_LICKS: list[Lick] = [
    # 8 — Simple ascending major triad, quarter notes
    [(0, 1.0), (4, 1.0), (7, 1.0), (12, 1.0)],

    # 9 — Major bebop run (eighths)
    [(0, 0.5), (2, 0.5), (4, 0.5), (5, 0.5), (7, 0.5), (5, 0.5), (4, 0.5), (2, 0.5)],

    # 10 — Major scale ascent with decorated top
    [(0, 0.5), (2, 0.5), (4, 0.5), (5, 0.5), (7, 0.5), (9, 0.5), (11, 0.5), (12, 0.5)],

    # 11 — Major descending with syncopation
    [(12, 1.5), (9, 0.5), (7, 0.5), (5, 0.5), (4, 0.5), (2, 0.5)],

    # 12 — Major pentatonic bounce
    [(0, 0.5), (4, 0.5), (7, 0.5), (9, 0.5), (7, 1.0), (4, 1.0)],

    # 13 — Major with upper neighbor
    [(7, 0.5), (9, 0.5), (7, 0.5), (5, 0.5), (4, 0.5), (5, 0.5), (4, 1.0)],
]

# ─── Dominant-7th licks ────────────────────────────────────────────────────────
DOMINANT_LICKS: list[Lick] = [
    # 14 — Dominant 7th arpeggio
    [(0, 1.0), (4, 1.0), (7, 1.0), (10, 1.0)],

    # 15 — Blues dominant run
    [(0, 0.5), (4, 0.5), (6, 0.5), (7, 0.5), (10, 0.5), (7, 0.5), (6, 0.5), (4, 0.5)],

    # 16 — Dominant mixolydian line
    [(0, 0.5), (2, 0.5), (4, 0.5), (7, 0.5), (10, 0.5), (9, 0.5), (7, 0.5), (4, 0.5)],

    # 17 — Dominant with b7 resolution
    [(10, 0.5), (9, 0.5), (7, 0.5), (5, 0.5), (4, 0.5), (2, 0.5), (0, 1.0)],
]

# ─── Universal licks (work over any chord quality) ────────────────────────────
UNIVERSAL_LICKS: list[Lick] = [
    # 18 — Root → octave step sequence
    [(0, 0.5), (2, 0.5), (4, 0.5), (5, 0.5), (7, 0.5), (5, 0.5), (4, 0.5), (0, 0.5)],

    # 19 — Chromatic approach into root
    [(-2, 0.5), (-1, 0.5), (0, 1.0), (7, 0.5), (5, 0.5), (3, 0.5), (0, 0.5)],

    # 20 — Call-and-response motif
    [(0, 0.5), (7, 0.5), (5, 0.5), (3, 0.5), (5, 0.5), (7, 0.5), (5, 0.5), (0, 0.5)],
]

# ─── Lookup helper ─────────────────────────────────────────────────────────────
def get_licks_for_quality(quality: ChordQuality) -> list[Lick]:
    """Return a pool of licks suitable for the given chord quality."""
    if quality in (ChordQuality.MINOR, ChordQuality.MIN7):
        return MINOR_LICKS + UNIVERSAL_LICKS
    if quality in (ChordQuality.DOM7,):
        return DOMINANT_LICKS + UNIVERSAL_LICKS
    if quality in (ChordQuality.MAJOR, ChordQuality.MAJ7):
        return MAJOR_LICKS + UNIVERSAL_LICKS
    # Diminished — use minor/universal
    return MINOR_LICKS + UNIVERSAL_LICKS
