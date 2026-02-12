from dictados.domain.note import Note
from dictados.domain.pitch import Pitch


def test_note_end_tick():
    note = Note(pitch=Pitch.from_midi(60), start_tick=10, duration_ticks=20)
    assert note.end_tick == 30
