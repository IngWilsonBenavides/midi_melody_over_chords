from __future__ import annotations

from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.domain.time_signature import TimeSignature
from dictados.generators.rhythm import RhythmEngine, Subdivision
from dictados.generators.sequence import SequenceApplicator
from dictados.generators.voicing import VoicingEngine


class PhraseBuilder:
    def __init__(self, voicing_engine: VoicingEngine, rhythm_engine: RhythmEngine):
        self.voicing_engine = voicing_engine
        self.rhythm_engine = rhythm_engine

    def build_phrase(
        self,
        chords: list,
        pattern: str,
        subdivision: Subdivision,
        time_signature: TimeSignature,
        ppqn: int,
    ) -> Phrase:
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
