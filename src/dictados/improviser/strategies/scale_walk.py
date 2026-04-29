"""Scale-walk improvisation strategy.

Walks stepwise along the chord's associated scale, with occasional direction
changes and rhythmic variation (quarter and eighth notes).
"""
from __future__ import annotations

import random

from dictados.domain.chord import Chord
from dictados.improviser.strategies.base import ImproStrategy
from dictados.improviser.theory import (
    get_scale_tones_in_range,
    nearest_chord_tone,
    nearest_scale_tone,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)
from dictados.improviser.voice_leading import apply_voice_leading


class ScaleWalkStrategy(ImproStrategy):
    """Stepwise scale walk with dynamic direction changes.

    The melody moves predominantly by step within the chord's associated
    scale, occasionally changing direction to create melodic arcs.
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
        scale_tones = get_scale_tones_in_range(chord, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI)
        if not scale_tones:
            root = nearest_chord_tone(prev_midi, chord)
            return [(root, measure_ticks)]

        # Find the nearest scale tone to start from.
        start = min(scale_tones, key=lambda m: abs(m - prev_midi))
        start_idx = scale_tones.index(start)

        # Build rhythm.
        quarter = ppqn
        eighth = ppqn // 2
        durations = self._make_rhythm(measure_ticks, quarter, eighth, rng)
        num_notes = len(durations)

        # Walk the scale, randomly changing direction.
        ascending = rng.random() < 0.55
        idx = start_idx
        midi_notes: list[int] = []

        for i in range(num_notes):
            midi_notes.append(scale_tones[idx])
            # Possibly change direction.
            if rng.random() < 0.15:
                ascending = not ascending
            # Advance index.
            if ascending:
                idx = min(idx + 1, len(scale_tones) - 1)
                if idx == len(scale_tones) - 1:
                    ascending = False
            else:
                idx = max(idx - 1, 0)
                if idx == 0:
                    ascending = True

        midi_notes = apply_voice_leading(midi_notes, prev_midi, max_leap=7)

        # Resolve last note to a chord tone.
        midi_notes[-1] = nearest_chord_tone(midi_notes[-1], chord)

        return list(zip(midi_notes, durations))

    @staticmethod
    def _make_rhythm(measure_ticks: int, quarter: int, eighth: int, rng: random.Random) -> list[int]:
        durations: list[int] = []
        ticks_used = 0
        while ticks_used < measure_ticks:
            remaining = measure_ticks - ticks_used
            if remaining <= quarter:
                durations.append(remaining)
                break
            if remaining >= 2 * eighth and rng.random() < 0.40:
                durations.append(eighth)
                durations.append(eighth)
                ticks_used += 2 * eighth
            else:
                durations.append(quarter)
                ticks_used += quarter
        return durations
