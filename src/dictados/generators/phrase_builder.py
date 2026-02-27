from __future__ import annotations

from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.domain.time_signature import TimeSignature
from dictados.generators.note_parser import parse_note_name
from dictados.generators.rhythm import RhythmEngine, Subdivision
from dictados.generators.rhythm_parser import parse_rhythm_list
from dictados.generators.sequence import SequenceApplicator
from dictados.generators.voicing import VoicingEngine
from dictados.domain.pitch import Pitch


class PhraseBuilder:
    def __init__(self, voicing_engine: VoicingEngine, rhythm_engine: RhythmEngine):
        self.voicing_engine = voicing_engine
        self.rhythm_engine = rhythm_engine

    def build_phrase(
        self,
        chords: list = None,
        pattern: str = None,
        subdivision: Subdivision = None,
        time_signature: TimeSignature = None,
        ppqn: int = 480,
    ) -> Phrase:
        """Build phrase from chords and patterns (original generated mode)."""
        measures: list[Measure] = []
        note_ticks = self.rhythm_engine.get_subdivision_ticks(subdivision)
        measure_ticks = time_signature.measure_ticks(ppqn)
        for i, chord in enumerate(chords):
            voicing = self.voicing_engine.get_next_voicing(chord)
            ordered = SequenceApplicator.apply_pattern(voicing, pattern)
            if len(ordered) * note_ticks != measure_ticks:
                raise ValueError("Notes do not fill the measure")
            start_tick = i * measure_ticks
            notes = []
            for j, pitch in enumerate(ordered):
                notes.append(
                    Note(
                        pitch=pitch,
                        start_tick=start_tick + j * note_ticks,
                        duration_ticks=note_ticks,
                        note_type="normal",
                    )
                )
            measures.append(
                Measure(
                    notes=notes,
                    chord=chord,
                    start_tick=start_tick,
                    duration_ticks=measure_ticks,
                )
            )
        return Phrase(measures=measures, ppqn=ppqn)

    def build_phrase_from_melody(
        self,
        melody_measures: list,
        ppqn: int = 480,
    ) -> Phrase:
        """Build phrase from specific melody.
        
        Args:
            melody_measures: list of MeasureSpec objects with notes and rhythms
            ppqn: parts per quarter note
            
        Returns:
            Phrase with explicit note sequence
        """
        measures: list[Measure] = []
        current_tick = 0
        
        for measure_spec in melody_measures:
            notes: list[Note] = []
            note_tick = current_tick
            
            # Parse rhythms to get ticks
            rhythm_ticks = parse_rhythm_list(measure_spec.rhythm, ppqn)
            
            # Create notes from parsed data
            for note_name, duration_ticks in zip(measure_spec.notes, rhythm_ticks):
                note_data = parse_note_name(note_name)
                
                # Create note with appropriate type
                note_type = note_data["note_type"]
                midi_number = note_data["midi_number"]
                
                if midi_number is not None:
                    pitch = Pitch.from_midi(midi_number)
                else:
                    pitch = None
                
                note = Note(
                    pitch=pitch,
                    start_tick=note_tick,
                    duration_ticks=duration_ticks,
                    velocity=100,
                    note_type=note_type,
                )
                notes.append(note)
                note_tick += duration_ticks
            
            # Calculate measure duration
            measure_ticks = sum(rhythm_ticks)
            
            measure = Measure(
                notes=notes,
                chord=None,  # No chord for specific melody
                start_tick=current_tick,
                duration_ticks=measure_ticks,
            )
            measures.append(measure)
            current_tick += measure_ticks
        
        return Phrase(measures=measures, ppqn=ppqn)

