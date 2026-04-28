from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dictados.domain.pitch import Pitch


class ChordQuality(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    DOM7 = "dom7"
    MAJ7 = "maj7"
    MIN7 = "min7"


@dataclass(frozen=True)
class Chord:
    root: Pitch
    quality: ChordQuality

    @property
    def root_pitch_class(self) -> int:
        return self.root.pitch_class

    def get_triad_pitch_classes(self) -> list[int]:
        if self.quality in (ChordQuality.MAJOR, ChordQuality.DOM7, ChordQuality.MAJ7):
            intervals = [0, 4, 7]
        elif self.quality in (ChordQuality.MINOR, ChordQuality.MIN7):
            intervals = [0, 3, 7]
        else:
            intervals = [0, 3, 6]
        return [(self.root_pitch_class + i) % 12 for i in intervals]

    def get_chord_pitch_classes(self) -> list[int]:
        pitch_classes = self.get_triad_pitch_classes()
        if self.quality == ChordQuality.DOM7:
            pitch_classes.append((self.root_pitch_class + 10) % 12)
        elif self.quality == ChordQuality.MAJ7:
            pitch_classes.append((self.root_pitch_class + 11) % 12)
        elif self.quality == ChordQuality.MIN7:
            pitch_classes.append((self.root_pitch_class + 10) % 12)
        return pitch_classes
