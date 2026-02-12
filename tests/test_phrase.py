from dictados.domain.phrase import Phrase, Measure
from dictados.domain.note import Note
from dictados.domain.pitch import Pitch
from dictados.domain.chord import Chord, ChordQuality


def test_phrase_structure():
    chord = Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR)
    note = Note(pitch=Pitch.from_midi(60), start_tick=0, duration_ticks=480)
    measure = Measure(notes=[note], chord=chord, start_tick=0, duration_ticks=1920)
    phrase = Phrase(measures=[measure], ppqn=480)
    assert phrase.measures[0].notes[0].pitch.midi_number == 60
