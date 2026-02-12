from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.pitch import Pitch
from dictados.domain.time_signature import TimeSignature
from dictados.generators.phrase_builder import PhraseBuilder
from dictados.generators.rhythm import RhythmEngine, Subdivision
from dictados.generators.voicing import VoicingEngine


def test_phrase_builder_basic():
    voicing = VoicingEngine(Pitch.from_midi(41), Pitch.from_midi(81))
    rhythm = RhythmEngine(ppqn=480)
    builder = PhraseBuilder(voicing, rhythm)

    chords = [
        Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR),
        Chord(root=Pitch.from_midi(69), quality=ChordQuality.MINOR),
    ]
    phrase = builder.build_phrase(
        chords=chords,
        pattern="1234",
        subdivision=Subdivision.QUARTER,
        time_signature=TimeSignature(4, 4),
        ppqn=480,
    )

    m1 = [n.pitch.midi_number for n in phrase.measures[0].notes]
    m2 = [n.pitch.midi_number for n in phrase.measures[1].notes]
    assert m1 == [43, 48, 52, 55]
    assert m2 == [45, 48, 52, 57]
