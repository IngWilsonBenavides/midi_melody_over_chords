from __future__ import annotations

from enum import Enum


class Subdivision(str, Enum):
    QUARTER = "quarter"
    EIGHTH = "eighth"
    HALF = "half"

    @staticmethod
    def from_string(value: str) -> "Subdivision":
        value = value.strip().lower()
        return Subdivision(value)


class RhythmEngine:
    def __init__(self, ppqn: int = 480):
        self.ppqn = ppqn

    def get_subdivision_ticks(self, subdivision: Subdivision) -> int:
        if subdivision == Subdivision.QUARTER:
            return self.ppqn
        if subdivision == Subdivision.EIGHTH:
            return self.ppqn // 2
        if subdivision == Subdivision.HALF:
            return self.ppqn * 2
        raise ValueError("Unsupported subdivision")
