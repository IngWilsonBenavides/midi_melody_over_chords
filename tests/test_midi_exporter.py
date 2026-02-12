from pathlib import Path

import mido

from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.pitch import Pitch
from dictados.domain.time_signature import TimeSignature
from dictados.generators.phrase_builder import PhraseBuilder
from dictados.generators.rhythm import RhythmEngine, Subdivision
from dictados.generators.voicing import VoicingEngine
from dictados.midi.exporter import MidiExporter


def test_midi_exporter_basic(tmp_path: Path):
    voicing = VoicingEngine(Pitch.from_midi(41), Pitch.from_midi(81))
    rhythm = RhythmEngine(ppqn=480)
    builder = PhraseBuilder(voicing, rhythm)
    chords = [Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR)]

    phrase = builder.build_phrase(
        chords=chords,
        pattern="1234",
        subdivision=Subdivision.QUARTER,
        time_signature=TimeSignature(4, 4),
        ppqn=480,
    )

    out_path = tmp_path / "test.mid"
    MidiExporter.export_phrase(
        phrase=phrase,
        tempo_bpm=100,
        output_path=out_path,
        time_signature=(4, 4),
        key="C",
    )

    midi = mido.MidiFile(out_path)
    assert midi.ticks_per_beat == 480
    note_messages = [msg for msg in midi.tracks[1] if msg.type == "note_on"]
    assert note_messages
    assert note_messages[0].note == 43
