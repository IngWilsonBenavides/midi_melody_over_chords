from __future__ import annotations

import dataclasses
import random

from dictados.domain.phrase import Measure, Phrase


def _audible_positions(phrase: Phrase) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    for measure_index, measure in enumerate(phrase.measures):
        for note_index, note in enumerate(measure.notes):
            if note.is_audible and note.pitch is not None:
                positions.append((measure_index, note_index))
    return positions


def _apply_pitch_order(phrase: Phrase, ordered_pitches) -> Phrase:
    measures: list[Measure] = []
    pitch_map = dict(zip(_audible_positions(phrase), ordered_pitches))
    for measure_index, measure in enumerate(phrase.measures):
        notes = []
        for note_index, note in enumerate(measure.notes):
            key = (measure_index, note_index)
            if key in pitch_map:
                notes.append(dataclasses.replace(note, pitch=pitch_map[key]))
            else:
                notes.append(note)
        measures.append(dataclasses.replace(measure, notes=notes))
    return dataclasses.replace(phrase, measures=measures)


def retrograde(phrase: Phrase) -> Phrase:
    positions = _audible_positions(phrase)
    pitches = [phrase.measures[m].notes[n].pitch for m, n in positions]
    return _apply_pitch_order(phrase, list(reversed(pitches)))


def rotate(phrase: Phrase, n: int) -> Phrase:
    positions = _audible_positions(phrase)
    pitches = [phrase.measures[m].notes[note_index].pitch for m, note_index in positions]
    if not pitches:
        return phrase
    offset = n % len(pitches)
    ordered = pitches[offset:] + pitches[:offset]
    return _apply_pitch_order(phrase, ordered)


def shuffle(phrase: Phrase, seed: int | None = None) -> Phrase:
    positions = _audible_positions(phrase)
    pitches = [phrase.measures[m].notes[n].pitch for m, n in positions]
    rng = random.Random(seed)
    rng.shuffle(pitches)
    return _apply_pitch_order(phrase, pitches)


def permute(phrase: Phrase, pattern: str) -> Phrase:
    positions = _audible_positions(phrase)
    pitches = [phrase.measures[m].notes[n].pitch for m, n in positions]
    indices = [int(char) - 1 for char in pattern]
    group_size = len(indices)
    ordered = []
    for start in range(0, len(pitches), group_size):
        group = pitches[start:start + group_size]
        if len(group) < group_size:
            ordered.extend(group)
            continue
        ordered.extend(group[index] for index in indices)
    return _apply_pitch_order(phrase, ordered)