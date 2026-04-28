"""Lick (phrase library) improvisation strategy.

Picks a pre-composed lick from the phrase library, transposes it to the
current chord root, and adjusts octave for smooth voice leading.
"""
from __future__ import annotations

import random

from dictados.domain.chord import Chord
from dictados.improviser.strategies.base import ImproStrategy
from dictados.improviser.phrase_library import get_licks_for_quality, Lick
from dictados.improviser.theory import (
    nearest_chord_tone,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)
from dictados.improviser.voice_leading import clamp_to_range, apply_voice_leading


class LickStrategy(ImproStrategy):
    """Transposes a lick from the phrase library to the current chord root.

    1. A lick is chosen at random from those matching the chord quality.
    2. Each interval in the lick is added to a chosen root MIDI number.
    3. The resulting sequence is adjusted for voice leading.
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
        licks = get_licks_for_quality(chord.quality)
        lick: Lick = rng.choice(licks)

        # Choose the root octave closest to prev_midi so the lick starts nearby.
        root_pc = chord.root.pitch_class
        candidates = [m for m in range(IMPRO_MIN_MIDI, IMPRO_MAX_MIDI + 1) if m % 12 == root_pc]
        root_midi = min(candidates, key=lambda m: abs(m - prev_midi)) if candidates else 60

        # Transpose lick intervals to absolute MIDI numbers.
        raw_midis = [root_midi + interval for (interval, _beats) in lick]
        raw_ticks = [int(beats * ppqn) for (_interval, beats) in lick]

        # Apply voice leading and clamp to range.
        midi_notes = apply_voice_leading(raw_midis, prev_midi, max_leap=14)

        # Scale ticks to fill the measure exactly.
        raw_total = sum(raw_ticks)
        if raw_total == 0:
            return [(nearest_chord_tone(prev_midi, chord), measure_ticks)]

        scaled_ticks = self._scale_durations(raw_ticks, measure_ticks)

        # Resolve last note to a chord tone.
        midi_notes[-1] = nearest_chord_tone(midi_notes[-1], chord)

        return list(zip(midi_notes, scaled_ticks))

    @staticmethod
    def _scale_durations(raw: list[int], target: int) -> list[int]:
        """Scale a list of tick durations so they sum exactly to *target*."""
        total = sum(raw)
        if total == 0 or not raw:
            return [target]
        # Proportional scaling with rounding.
        scaled = [max(1, int(round(d / total * target))) for d in raw]
        # Fix rounding error on the last element.
        diff = target - sum(scaled)
        scaled[-1] = max(1, scaled[-1] + diff)
        return scaled
