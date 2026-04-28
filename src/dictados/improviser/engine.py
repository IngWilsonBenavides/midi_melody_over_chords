"""ImproEngine — orchestrates all improvisation strategies.

Selects which strategy to use for each measure, maintains continuity via
``prev_midi``, implements call-and-response structure, and returns the
complete list of (midi, ticks) pairs for the full improvisation.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from dictados.domain.chord import Chord
from dictados.improviser.strategies.arpegio import ArpegioStrategy
from dictados.improviser.strategies.scale_walk import ScaleWalkStrategy
from dictados.improviser.strategies.lick import LickStrategy
from dictados.improviser.strategies.approach import ApproachToneStrategy
from dictados.improviser.strategies.motif import MotifStrategy
from dictados.improviser.strategies.weighted_random import WeightedRandomStrategy
from dictados.improviser.theory import nearest_chord_tone, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI

# Strategy weights: (strategy_instance, weight)
# Higher weight = more likely to be chosen
_STRATEGY_POOL = [
    (ArpegioStrategy(),       2),
    (ScaleWalkStrategy(),     3),
    (LickStrategy(),          3),
    (ApproachToneStrategy(),  2),
    (MotifStrategy(),         2),
    (WeightedRandomStrategy(), 2),
]


@dataclass
class ImproEngine:
    """Generates a full improvisation over a chord progression.

    Args:
        ppqn:        Pulses per quarter note.
        time_sig_num: Time-signature numerator (default 4).
        seed:        Optional random seed for reproducibility.
    """
    ppqn: int = 480
    time_sig_num: int = 4
    seed: Optional[int] = None
    _rng: random.Random = field(init=False)

    def __post_init__(self):
        self._rng = random.Random(self.seed)

    # ─── Public API ───────────────────────────────────────────────────────────

    def improvise(
        self,
        chords: list[Chord],
        start_midi: int = 60,
    ) -> list[list[tuple[int, int]]]:
        """Generate one measure of notes for each chord in *chords*.

        Args:
            chords:     Ordered list of chords (one per measure).
            start_midi: MIDI number of the note that precedes measure 0.

        Returns:
            A list of length ``len(chords)``; each element is a list of
            ``(midi_number, duration_ticks)`` tuples that fill one measure.
        """
        measure_ticks = self.time_sig_num * self.ppqn
        prev_midi = start_midi
        context: list[int] = []
        result: list[list[tuple[int, int]]] = []

        strategies, weights = zip(*_STRATEGY_POOL)

        for i, chord in enumerate(chords):
            # Call-and-response: even measures are "call" (active), odd are "response" (settling).
            is_call = (i % 2 == 0)

            if is_call:
                # Active measures: lick, scale walk, arpeggio, weighted random.
                active_pool = [
                    (LickStrategy(),          3),
                    (ScaleWalkStrategy(),     3),
                    (ArpegioStrategy(),       2),
                    (WeightedRandomStrategy(), 2),
                ]
            else:
                # Response measures: approach tones, motif development, arpeggio.
                active_pool = [
                    (ApproachToneStrategy(),  3),
                    (MotifStrategy(),         3),
                    (ArpegioStrategy(),       2),
                    (ScaleWalkStrategy(),     1),
                ]

            strats, wts = zip(*active_pool)
            chosen = self._rng.choices(strats, weights=wts, k=1)[0]

            notes = chosen.generate(
                chord=chord,
                measure_ticks=measure_ticks,
                ppqn=self.ppqn,
                prev_midi=prev_midi,
                rng=self._rng,
                context=context if context else None,
            )

            # Safety: ensure total ticks match measure_ticks.
            notes = self._fix_duration(notes, measure_ticks, chord)

            result.append(notes)

            # Update continuity state.
            if notes:
                prev_midi = notes[-1][0]
                context.extend(m for m, _ in notes)
                # Keep context window small.
                context = context[-16:]

        return result

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _fix_duration(
        self,
        notes: list[tuple[int, int]],
        measure_ticks: int,
        chord: Chord,
    ) -> list[tuple[int, int]]:
        """Ensure *notes* sums to exactly *measure_ticks*."""
        if not notes:
            root = nearest_chord_tone(60, chord)
            return [(root, measure_ticks)]

        total = sum(d for _, d in notes)
        if total == measure_ticks:
            return notes

        midi_list = [m for m, _ in notes]
        dur_list = [d for _, d in notes]

        if total > measure_ticks:
            # Trim trailing notes.
            acc = 0
            new_m, new_d = [], []
            for m, d in zip(midi_list, dur_list):
                if acc + d <= measure_ticks:
                    new_m.append(m)
                    new_d.append(d)
                    acc += d
                elif acc < measure_ticks:
                    new_m.append(m)
                    new_d.append(measure_ticks - acc)
                    break
            if not new_m:
                new_m = [midi_list[0]]
                new_d = [measure_ticks]
            return list(zip(new_m, new_d))
        else:
            # Extend last note.
            dur_list[-1] += measure_ticks - total
            return list(zip(midi_list, dur_list))
