from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.domain.pitch import Pitch
from dictados.domain.scale import Scale
from dictados.transformations import (
    augment,
    diminish,
    invert,
    permute,
    pitch_shift_degrees,
    retrograde,
    rotate,
    shuffle,
    transpose,
)


def _make_phrase(midis: list[int]) -> Phrase:
    notes = [
        Note(pitch=Pitch.from_midi(midi), start_tick=index * 480, duration_ticks=480)
        for index, midi in enumerate(midis)
    ]
    measure = Measure(
        notes=notes,
        chord=Chord(root=Pitch.from_midi(60), quality=ChordQuality.MAJOR),
        start_tick=0,
        duration_ticks=len(notes) * 480,
    )
    return Phrase(measures=[measure], ppqn=480)


def _audible_midis(phrase: Phrase) -> list[int]:
    return [note.pitch.midi_number for measure in phrase.measures for note in measure.notes if note.pitch]


def test_transpose_up():
    phrase = _make_phrase([60, 62, 64])
    transposed = transpose(phrase, 2)
    assert _audible_midis(transposed) == [62, 64, 66]


def test_transpose_snap_to_scale():
    phrase = _make_phrase([60])
    transposed = transpose(phrase, 1, Scale.from_string("C"))
    assert _audible_midis(transposed)[0] in (60, 62)


def test_invert_around_first_note():
    phrase = _make_phrase([60, 62, 64])
    inverted = invert(phrase)
    assert _audible_midis(inverted) == [60, 58, 56]


def test_pitch_shift_degrees():
    phrase = _make_phrase([60, 67])
    shifted = pitch_shift_degrees(phrase, Scale.from_string("C"), 2)
    assert _audible_midis(shifted) == [64, 71]


def test_retrograde():
    phrase = _make_phrase([60, 62, 64, 65])
    transformed = retrograde(phrase)
    assert _audible_midis(transformed) == [65, 64, 62, 60]


def test_rotate():
    phrase = _make_phrase([60, 62, 64, 65, 67])
    transformed = rotate(phrase, 2)
    assert _audible_midis(transformed) == [64, 65, 67, 60, 62]


def test_shuffle_reproducible():
    phrase = _make_phrase([60, 62, 64, 65, 67])
    one = shuffle(phrase, seed=7)
    two = shuffle(phrase, seed=7)
    assert _audible_midis(one) == _audible_midis(two)


def test_permute():
    phrase = _make_phrase([60, 62, 64, 65])
    transformed = permute(phrase, "4321")
    assert _audible_midis(transformed) == [65, 64, 62, 60]


def test_augment():
    phrase = _make_phrase([60, 62])
    transformed = augment(phrase, factor=2)
    assert transformed.measures[0].notes[0].duration_ticks == 960
    assert transformed.measures[0].notes[1].start_tick == 960


def test_diminish():
    phrase = _make_phrase([60, 62])
    transformed = diminish(phrase, factor=2)
    assert transformed.measures[0].notes[0].duration_ticks == 240
    assert transformed.measures[0].notes[1].start_tick == 240