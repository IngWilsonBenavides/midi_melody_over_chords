"""Approach-tone improvisation strategy.

Targets chord tones and approaches them from 1–2 semitones away, creating
tension-and-resolution motion characteristic of jazz improvisation.
"""
from __future__ import annotations

import random

from dictados.domain.chord import Chord
from dictados.improviser.strategies.base import ImproStrategy
from dictados.improviser.theory import (
    get_chord_tones_in_range,
    get_scale_tones_in_range,
    nearest_chord_tone,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)
from dictados.improviser.voice_leading import apply_voice_leading, clamp_to_range


class ApproachToneStrategy(ImproStrategy):
    """Builds phrases that approach chord tones by step or semitone.

    Pattern for each target chord tone:
      [approach_note, target_chord_tone]

    Multiple approach-resolution pairs are chained to fill the measure.
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
            return [(nearest_chord_tone(prev_midi, chord), measure_ticks)]

        quarter = ppqn
        eighth = ppqn // 2

        pairs: list[tuple[int, int]] = []   # (approach_midi, target_midi)
        current = prev_midi

        # Build approach-resolution pairs until we have enough to fill measure.
        budget = measure_ticks
        while budget > 0:
            # Pick a target chord tone close to current.
            target = min(chord_tones, key=lambda m: abs(m - current))
            # Chromatic approach from above or below (or whole-step).
            offset = rng.choice([-2, -1, 1, 2])
            approach = clamp_to_range(target + offset)
            pairs.append((approach, target))
            current = target
            budget -= 2 * eighth
            if budget <= 0:
                break

        # Turn pairs into flat midi + duration lists.
        midi_notes: list[int] = []
        durations: list[int] = []
        for approach, target in pairs:
            midi_notes.append(approach)
            midi_notes.append(target)
            durations.append(eighth)
            durations.append(eighth)

        # Trim or pad to fill exactly measure_ticks.
        midi_notes, durations = self._fit_to_measure(midi_notes, durations, measure_ticks, chord, rng)

        midi_notes = apply_voice_leading(midi_notes, prev_midi, max_leap=10)
        midi_notes[-1] = nearest_chord_tone(midi_notes[-1], chord)

        return list(zip(midi_notes, durations))

    @staticmethod
    def _fit_to_measure(
        midi_notes: list[int],
        durations: list[int],
        measure_ticks: int,
        chord: Chord,
        rng: random.Random,
    ) -> tuple[list[int], list[int]]:
        """Trim or extend notes/durations to sum exactly to *measure_ticks*."""
        total = sum(durations)
        if total == measure_ticks:
            return midi_notes, durations
        if total > measure_ticks:
            # Drop notes from the end until we're within budget.
            while sum(durations) > measure_ticks and durations:
                midi_notes.pop()
                durations.pop()
            # Stretch the last note.
            if durations:
                diff = measure_ticks - sum(durations)
                durations[-1] += diff
            else:
                ct = nearest_chord_tone(60, chord)
                return [ct], [measure_ticks]
        else:
            # Extend the last duration.
            durations[-1] += measure_ticks - total
        return midi_notes, durations
