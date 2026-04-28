"""Weighted-random improvisation strategy.

Picks each note at random with weights favouring:
- Chord tones    60 %
- Scale tones    30 %
- Chromatic      10 %

Voice leading constraints ensure no leap exceeds MAX_MELODIC_LEAP semitones.
"""
from __future__ import annotations

import random

from dictados.domain.chord import Chord
from dictados.improviser.strategies.base import ImproStrategy
from dictados.improviser.theory import (
    get_chord_tones_in_range,
    get_scale_tones_in_range,
    get_chromatic_tones_in_range,
    nearest_chord_tone,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)
from dictados.improviser.voice_leading import apply_voice_leading, clamp_to_range

_CHORD_WEIGHT = 0.60
_SCALE_WEIGHT = 0.30
_CHROM_WEIGHT = 0.10


class WeightedRandomStrategy(ImproStrategy):
    """Non-deterministic strategy using weighted random note selection.

    The pool of candidates is segmented into chord tones, scale-only tones
    (scale tones that are *not* chord tones), and chromatic tones (all others).
    Each note is drawn according to the configured weights.
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
        scale_tones = get_scale_tones_in_range(chord, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI)
        all_tones = get_chromatic_tones_in_range(IMPRO_MIN_MIDI, IMPRO_MAX_MIDI)

        chord_set = set(chord_tones)
        scale_only = [m for m in scale_tones if m not in chord_set]
        chrom_only = [m for m in all_tones if m not in set(scale_tones)]

        # Build rhythm.
        quarter = ppqn
        eighth = ppqn // 2
        durations = self._make_rhythm(measure_ticks, quarter, eighth, rng)

        midi_notes: list[int] = []
        for i, dur in enumerate(durations):
            roll = rng.random()
            if roll < _CHORD_WEIGHT and chord_tones:
                pool = chord_tones
            elif roll < _CHORD_WEIGHT + _SCALE_WEIGHT and scale_only:
                pool = scale_only
            elif chrom_only:
                pool = chrom_only
            else:
                pool = chord_tones or scale_tones or all_tones

            # Weight toward notes near prev_midi for smoother motion.
            last = midi_notes[-1] if midi_notes else prev_midi
            note = rng.choices(pool, weights=[1 / (abs(m - last) + 1) for m in pool], k=1)[0]
            midi_notes.append(note)

        midi_notes = apply_voice_leading(midi_notes, prev_midi, max_leap=10)
        midi_notes[-1] = nearest_chord_tone(midi_notes[-1], chord)

        return list(zip(midi_notes, durations))

    @staticmethod
    def _make_rhythm(measure_ticks: int, quarter: int, eighth: int, rng: random.Random) -> list[int]:
        durations: list[int] = []
        ticks_used = 0
        dot_q = quarter + eighth
        while ticks_used < measure_ticks:
            remaining = measure_ticks - ticks_used
            if remaining <= quarter:
                durations.append(remaining)
                break
            roll = rng.random()
            if roll < 0.35 and remaining >= 2 * eighth:
                durations.append(eighth)
                durations.append(eighth)
                ticks_used += 2 * eighth
            elif roll < 0.50 and remaining >= dot_q:
                # Dotted quarter
                durations.append(dot_q)
                ticks_used += dot_q
            else:
                durations.append(quarter)
                ticks_used += quarter
        return durations
