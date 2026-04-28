from __future__ import annotations

import dataclasses
from typing import Callable

from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.domain.pitch import MAX_MIDI, MIN_MIDI, Pitch
from dictados.domain.scale import Scale


def _replace_pitch(note: Note, midi_number: int) -> Note:
    clamped = max(MIN_MIDI, min(MAX_MIDI, midi_number))
    return dataclasses.replace(note, pitch=Pitch.from_midi(clamped))


def _map_audible_notes(phrase: Phrase, transform: Callable[[Note], Note]) -> Phrase:
    measures: list[Measure] = []
    for measure in phrase.measures:
        notes = [
            transform(note) if note.is_audible and note.pitch is not None else note
            for note in measure.notes
        ]
        measures.append(dataclasses.replace(measure, notes=notes))
    return dataclasses.replace(phrase, measures=measures)


def transpose(phrase: Phrase, semitones: int, scale: Scale | None = None) -> Phrase:
    def transform(note: Note) -> Note:
        midi_number = note.pitch.midi_number + semitones
        if scale is not None:
            midi_number = scale.nearest_scale_pitch(midi_number)
        return _replace_pitch(note, midi_number)

    return _map_audible_notes(phrase, transform)


def invert(phrase: Phrase, axis_pitch: Pitch | None = None) -> Phrase:
    audible_midis = [
        note.pitch.midi_number
        for measure in phrase.measures
        for note in measure.notes
        if note.is_audible and note.pitch is not None
    ]
    if not audible_midis:
        return phrase

    axis = axis_pitch.midi_number if axis_pitch is not None else audible_midis[0]

    def transform(note: Note) -> Note:
        interval = note.pitch.midi_number - axis
        return _replace_pitch(note, axis - interval)

    return _map_audible_notes(phrase, transform)


def pitch_shift_degrees(phrase: Phrase, scale: Scale, degrees: int) -> Phrase:
    scale_pcs = scale.get_scale_pitch_classes()

    def shift_midi(midi_number: int) -> int:
        normalized = scale.nearest_scale_pitch(midi_number)
        octave, pitch_class = divmod(normalized, 12)
        index = scale_pcs.index(pitch_class)
        shifted_index = index + degrees
        octave += shifted_index // len(scale_pcs)
        shifted_pc = scale_pcs[shifted_index % len(scale_pcs)]
        return octave * 12 + shifted_pc

    def transform(note: Note) -> Note:
        return _replace_pitch(note, shift_midi(note.pitch.midi_number))

    return _map_audible_notes(phrase, transform)