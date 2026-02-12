from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.pitch import Pitch

NOTE_TO_PC = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

MAJOR_DEGREES = [0, 2, 4, 5, 7, 9, 11]
MINOR_DEGREES = [0, 2, 3, 5, 7, 8, 10]


class ScaleMode(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


@dataclass(frozen=True)
class Scale:
    tonic_pc: int
    mode: ScaleMode

    @staticmethod
    def from_string(key: str) -> "Scale":
        if not key:
            raise ValueError("Key is required")
        key = key.strip()
        is_minor = key.lower().endswith("m") and len(key) > 1
        tonic_name = key[:-1] if is_minor else key
        tonic_name = tonic_name.upper()
        if tonic_name not in NOTE_TO_PC:
            raise ValueError(f"Unknown key: {key}")
        tonic_pc = NOTE_TO_PC[tonic_name]
        mode = ScaleMode.MINOR if is_minor else ScaleMode.MAJOR
        return Scale(tonic_pc=tonic_pc, mode=mode)

    def degree_pitch_class(self, degree: int) -> int:
        if degree < 1 or degree > 7:
            raise ValueError("Degree must be 1-7")
        degrees = MINOR_DEGREES if self.mode == ScaleMode.MINOR else MAJOR_DEGREES
        return (self.tonic_pc + degrees[degree - 1]) % 12

    def chord_from_degree(self, degree: int, quality: ChordQuality) -> Chord:
        root_pc = self.degree_pitch_class(degree)
        root = Pitch.from_midi(60 + root_pc)
        return Chord(root=root, quality=quality)
