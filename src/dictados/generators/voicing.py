from __future__ import annotations

from dataclasses import dataclass, field

from dictados.domain.chord import Chord
from dictados.domain.pitch import Pitch


@dataclass
class VoicingEngine:
    range_low: Pitch
    range_high: Pitch
    _voicing_state: dict[Chord, int] = field(default_factory=dict)

    def get_next_voicing(self, chord: Chord) -> list[Pitch]:
        base_pitch, base_index = self._get_base_pitch_and_index(chord)
        offset = self._voicing_state.get(chord, 0)
        notes = self._build_sequence_for_chord(chord, base_pitch, base_index, offset + 4)
        voicing = notes[offset:offset + 4]
        if voicing[-1].midi_number > self.range_high.midi_number:
            raise ValueError("Voicing exceeds range")
        self._voicing_state[chord] = offset + 1
        return voicing

    def _get_base_pitch_and_index(self, chord: Chord) -> tuple[Pitch, int]:
        chord_pcs = chord.get_triad_pitch_classes()
        for midi in range(self.range_low.midi_number, self.range_high.midi_number + 1):
            if midi % 12 in chord_pcs:
                return Pitch.from_midi(midi), chord_pcs.index(midi % 12)
        raise ValueError("No chord tone found in range")

    def _build_sequence_for_chord(
        self,
        chord: Chord,
        start_pitch: Pitch,
        start_index: int,
        length: int,
    ) -> list[Pitch]:
        chord_pcs = chord.get_triad_pitch_classes()
        seq: list[Pitch] = [start_pitch]
        index = start_index
        current_midi = start_pitch.midi_number
        while len(seq) < length:
            index = (index + 1) % len(chord_pcs)
            next_pc = chord_pcs[index]
            delta = (next_pc - (current_midi % 12)) % 12
            if delta == 0:
                delta = 12
            current_midi += delta
            seq.append(Pitch.from_midi(current_midi))
        return seq
