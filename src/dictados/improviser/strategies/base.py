"""Abstract base class for improvisation strategies."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Optional

from dictados.domain.chord import Chord


class ImproStrategy(ABC):
    """Interface for all improvisation strategies.

    Each strategy generates a list of ``(midi_number, duration_ticks)`` tuples
    representing one measure of melodic improvisation.
    """

    @abstractmethod
    def generate(
        self,
        chord: Chord,
        measure_ticks: int,
        ppqn: int,
        prev_midi: int,
        rng: random.Random,
        context: Optional[list[int]] = None,
    ) -> list[tuple[int, int]]:
        """Generate notes for one measure.

        Args:
            chord:        The chord sounding during this measure.
            measure_ticks: Total duration of the measure in MIDI ticks.
            ppqn:         Pulses per quarter note.
            prev_midi:    MIDI number of the last note in the previous measure.
            rng:          Random number generator (seeded externally for reproducibility).
            context:      Optional list of recent MIDI note numbers (for motif strategies).

        Returns:
            List of ``(midi, ticks)`` pairs that sum to exactly *measure_ticks*.
        """
