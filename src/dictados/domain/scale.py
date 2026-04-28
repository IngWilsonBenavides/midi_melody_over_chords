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
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    LOCRIAN = "locrian"


MODE_DEGREES = {
    ScaleMode.MAJOR: MAJOR_DEGREES,
    ScaleMode.MINOR: MINOR_DEGREES,
    ScaleMode.HARMONIC_MINOR: [0, 2, 3, 5, 7, 8, 11],
    ScaleMode.MELODIC_MINOR: [0, 2, 3, 5, 7, 9, 11],
    ScaleMode.DORIAN: [0, 2, 3, 5, 7, 9, 10],
    ScaleMode.PHRYGIAN: [0, 1, 3, 5, 7, 8, 10],
    ScaleMode.LYDIAN: [0, 2, 4, 6, 7, 9, 11],
    ScaleMode.MIXOLYDIAN: [0, 2, 4, 5, 7, 9, 10],
    ScaleMode.LOCRIAN: [0, 1, 3, 5, 6, 8, 10],
}

MODE_SUFFIXES = {
    "dor": ScaleMode.DORIAN,
    "phr": ScaleMode.PHRYGIAN,
    "lyd": ScaleMode.LYDIAN,
    "mix": ScaleMode.MIXOLYDIAN,
    "loc": ScaleMode.LOCRIAN,
    "hm": ScaleMode.HARMONIC_MINOR,
    "mm": ScaleMode.MELODIC_MINOR,
}


@dataclass(frozen=True)
class Scale:
    tonic_pc: int
    mode: ScaleMode

    @staticmethod
    def from_string(key: str) -> "Scale":
        if not key:
            raise ValueError("Key is required")
        key = key.strip()
        lower_key = key.lower()
        mode = ScaleMode.MAJOR
        tonic_name = key
        for suffix, suffix_mode in MODE_SUFFIXES.items():
            if lower_key.endswith(suffix):
                tonic_name = key[:-len(suffix)]
                mode = suffix_mode
                break
        else:
            is_minor = lower_key.endswith("m") and len(key) > 1
            tonic_name = key[:-1] if is_minor else key
            mode = ScaleMode.MINOR if is_minor else ScaleMode.MAJOR
        tonic_name = tonic_name.upper()
        if tonic_name not in NOTE_TO_PC:
            raise ValueError(f"Unknown key: {key}")
        tonic_pc = NOTE_TO_PC[tonic_name]
        return Scale(tonic_pc=tonic_pc, mode=mode)

    def degree_pitch_class(self, degree: int) -> int:
        if degree < 1 or degree > 7:
            raise ValueError("Degree must be 1-7")
        degrees = MODE_DEGREES[self.mode]
        return (self.tonic_pc + degrees[degree - 1]) % 12

    def get_scale_pitch_classes(self) -> list[int]:
        degrees = MODE_DEGREES[self.mode]
        return [(self.tonic_pc + degree) % 12 for degree in degrees]

    def nearest_scale_pitch(self, midi: int) -> int:
        scale_pcs = self.get_scale_pitch_classes()
        pitch_class = midi % 12
        if pitch_class in scale_pcs:
            return midi

        best_delta = 12
        for scale_pc in scale_pcs:
            delta = (scale_pc - pitch_class) % 12
            if delta > 6:
                delta -= 12
            if abs(delta) < abs(best_delta):
                best_delta = delta
        return midi + best_delta

    def chord_from_degree(self, degree: int, quality: ChordQuality) -> Chord:
        root_pc = self.degree_pitch_class(degree)
        root = Pitch.from_midi(60 + root_pc)
        return Chord(root=root, quality=quality)
