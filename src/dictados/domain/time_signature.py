from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeSignature:
    numerator: int
    denominator: int

    def measure_ticks(self, ppqn: int) -> int:
        if self.denominator == 0:
            raise ValueError("Invalid denominator")
        beat_ticks = ppqn * (4 / self.denominator)
        return int(self.numerator * beat_ticks)
