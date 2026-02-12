from __future__ import annotations

from dataclasses import dataclass

from dictados.domain.pitch import Pitch


@dataclass(frozen=True)
class Note:
    pitch: Pitch
    start_tick: int
    duration_ticks: int
    velocity: int = 100

    @property
    def end_tick(self) -> int:
        return self.start_tick + self.duration_ticks
