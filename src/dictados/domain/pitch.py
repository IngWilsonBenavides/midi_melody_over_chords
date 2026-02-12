from __future__ import annotations

from dataclasses import dataclass

MIN_MIDI = 41
MAX_MIDI = 81


@dataclass(frozen=True)
class Pitch:
    midi_number: int

    @staticmethod
    def from_midi(midi: int) -> "Pitch":
        if midi < MIN_MIDI or midi > MAX_MIDI:
            raise ValueError(f"MIDI out of range: {midi}")
        return Pitch(midi_number=int(midi))

    @property
    def pitch_class(self) -> int:
        return self.midi_number % 12

    def __lt__(self, other: "Pitch") -> bool:
        return self.midi_number < other.midi_number
