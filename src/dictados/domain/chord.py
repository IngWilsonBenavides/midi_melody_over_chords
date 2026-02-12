from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dictados.domain.pitch import Pitch


class ChordQuality(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"


@dataclass(frozen=True)
class Chord:
    root: Pitch
    quality: ChordQuality

    @property
    def root_pitch_class(self) -> int:
        return self.root.pitch_class

    def get_triad_pitch_classes(self) -> list[int]:
        if self.quality == ChordQuality.MAJOR:
            intervals = [0, 4, 7]
        elif self.quality == ChordQuality.MINOR:
            intervals = [0, 3, 7]
        else:
            intervals = [0, 3, 6]
        return [(self.root_pitch_class + i) % 12 for i in intervals]
