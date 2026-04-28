"""Motif development improvisation strategy.

Takes a seed motif (the first few notes from the melodic context) and
develops it through transposition, inversion, rhythmic augmentation, or
retrograde — classic compositional techniques.
"""
from __future__ import annotations

import random

from dictados.domain.chord import Chord
from dictados.improviser.strategies.base import ImproStrategy
from dictados.improviser.strategies.scale_walk import ScaleWalkStrategy
from dictados.improviser.theory import (
    get_scale_tones_in_range,
    nearest_chord_tone,
    nearest_scale_tone,
    IMPRO_MIN_MIDI,
    IMPRO_MAX_MIDI,
)
from dictados.improviser.voice_leading import apply_voice_leading, clamp_to_range

_MOTIF_LEN = 4  # number of context notes to use as the motif seed


class MotifStrategy(ImproStrategy):
    """Develops a short motif extracted from previous melodic context.

    Supported transformations:
    - ``transpose``: Shift the motif by ±2–5 semitones.
    - ``retrograde``: Reverse the motif.
    - ``invert``: Invert intervals around the first note.
    - ``augment``: Double all durations (may be trimmed to fit).
    - ``diminution``: Halve all durations, repeat the motif.

    Falls back to :class:`ScaleWalkStrategy` when no context is available.
    """

    def __init__(self):
        self._fallback = ScaleWalkStrategy()

    def generate(
        self,
        chord: Chord,
        measure_ticks: int,
        ppqn: int,
        prev_midi: int,
        rng: random.Random,
        context=None,
    ) -> list[tuple[int, int]]:
        if not context or len(context) < 2:
            return self._fallback.generate(chord, measure_ticks, ppqn, prev_midi, rng, context)

        # Extract motif: last N notes from context.
        motif_midi = list(context[-_MOTIF_LEN:])

        # Convert absolute MIDIs to intervals relative to the first motif note.
        intervals = [motif_midi[i] - motif_midi[i - 1] for i in range(1, len(motif_midi))]

        # Choose transformation.
        transformation = rng.choice(["transpose", "retrograde", "invert", "diminution"])

        if transformation == "retrograde":
            intervals = list(reversed(intervals))
        elif transformation == "invert":
            intervals = [-iv for iv in intervals]
        elif transformation == "transpose":
            shift = rng.choice([-5, -3, -2, 2, 3, 5, 7])
            intervals = [iv for iv in intervals]  # keep same; shift start
            motif_midi[0] = clamp_to_range(motif_midi[0] + shift)

        # Rebuild absolute MIDIs from intervals.
        developed: list[int] = [motif_midi[0]]
        for iv in intervals:
            developed.append(clamp_to_range(developed[-1] + iv))

        # Build durations: quarter notes by default, halved for diminution.
        quarter = ppqn
        eighth = ppqn // 2
        if transformation == "diminution":
            base_dur = eighth
            # Repeat motif to fill measure.
            developed = developed * max(1, (measure_ticks // (len(developed) * eighth) + 1))
        else:
            base_dur = quarter

        durations = [base_dur] * len(developed)

        # Fit to measure_ticks.
        developed, durations = self._fit(developed, durations, measure_ticks, chord)

        developed = apply_voice_leading(developed, prev_midi, max_leap=10)
        developed[-1] = nearest_chord_tone(developed[-1], chord)

        return list(zip(developed, durations))

    @staticmethod
    def _fit(
        midi_notes: list[int],
        durations: list[int],
        measure_ticks: int,
        chord: Chord,
    ) -> tuple[list[int], list[int]]:
        """Trim or extend to sum to *measure_ticks*."""
        total = sum(durations)
        if total == measure_ticks:
            return midi_notes, durations
        if total > measure_ticks:
            # Trim trailing notes.
            acc = 0
            new_m, new_d = [], []
            for m, d in zip(midi_notes, durations):
                if acc + d <= measure_ticks:
                    new_m.append(m)
                    new_d.append(d)
                    acc += d
                else:
                    # Last partial note.
                    new_m.append(m)
                    new_d.append(measure_ticks - acc)
                    break
            return new_m, new_d
        else:
            durations[-1] += measure_ticks - total
            return midi_notes, durations
