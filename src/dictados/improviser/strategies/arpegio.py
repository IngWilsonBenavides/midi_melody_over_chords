"""Directed arpeggio improvisation strategy.

Plays chord tones in ascending or descending melodic order, with optional
rhythmic variation (quarter notes and eighths).
"""
from __future__ import annotations

import random

from dictados.domain.chord import Chord
from dictados.improviser.strategies.base import ImproStrategy
from dictados.improviser.theory import (
    get_chord_tones_in_range,
    nearest_chord_tone,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)
from dictados.improviser.voice_leading import apply_voice_leading, clamp_to_range


class ArpegioStrategy(ImproStrategy):
    """Arpeggio-based improvisation with rhythmic variety.

    The arpeggio starts near *prev_midi*, either ascending or descending, and
    wraps around the range.  A small random chance introduces eighth-note
    pairs to add rhythmic interest.
    """

    def generate(
        self,
        chord: Chord,
        measure_ticks: int,
        ppqn: int,
        prev_midi: int,
        rng: random.Random,
        context=None,
    ) -> list[tuple[int, int]]:
        chord_tones = get_chord_tones_in_range(chord, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI)
        if not chord_tones:
            # Fallback: whole-measure root
            root = clamp_to_range(chord.root.pitch_class + 60)
            return [(root, measure_ticks)]

        # Start from the chord tone nearest to prev_midi.
        start = min(chord_tones, key=lambda m: abs(m - prev_midi))
        start_idx = chord_tones.index(start)

        # Choose direction randomly (slightly biased toward ascending).
        ascending = rng.random() < 0.6
        if ascending:
            pool = chord_tones[start_idx:] + chord_tones[:start_idx]
        else:
            pool = list(reversed(chord_tones[:start_idx + 1])) + list(
                reversed(chord_tones[start_idx + 1:])
            )

        # Build a rhythm pattern that fills the measure.
        quarter = ppqn
        eighth = ppqn // 2
        notes_dur = self._make_rhythm(measure_ticks, quarter, eighth, rng)

        midi_notes = []
        for i, _dur in enumerate(notes_dur):
            midi_notes.append(pool[i % len(pool)])

        midi_notes = apply_voice_leading(midi_notes, start, max_leap=12)

        # Ensure the last note is a chord tone (resolution).
        midi_notes[-1] = nearest_chord_tone(midi_notes[-1], chord)

        return list(zip(midi_notes, notes_dur))

    # ─── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _make_rhythm(measure_ticks: int, quarter: int, eighth: int, rng: random.Random) -> list[int]:
        """Return a list of tick durations that sum to *measure_ticks*."""
        beats_total = measure_ticks // quarter
        durations: list[int] = []
        ticks_used = 0

        while ticks_used < measure_ticks:
            remaining = measure_ticks - ticks_used
            if remaining <= quarter:
                durations.append(remaining)
                break
            # 30% chance of eighth-note pair.
            if remaining >= 2 * eighth and rng.random() < 0.30:
                durations.append(eighth)
                durations.append(eighth)
                ticks_used += 2 * eighth
            else:
                durations.append(quarter)
                ticks_used += quarter

        return durations
