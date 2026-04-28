from __future__ import annotations

import dataclasses

from dictados.domain.phrase import Measure, Phrase

MIN_TICKS = 30


def augment(phrase: Phrase, factor: int = 2) -> Phrase:
    measures: list[Measure] = []
    for measure in phrase.measures:
        notes = [
            dataclasses.replace(
                note,
                start_tick=note.start_tick * factor,
                duration_ticks=note.duration_ticks * factor,
            )
            for note in measure.notes
        ]
        measures.append(
            dataclasses.replace(
                measure,
                notes=notes,
                start_tick=measure.start_tick * factor,
                duration_ticks=measure.duration_ticks * factor,
            )
        )
    return dataclasses.replace(phrase, measures=measures)


def diminish(phrase: Phrase, factor: int = 2) -> Phrase:
    measures: list[Measure] = []
    for measure in phrase.measures:
        notes = [
            dataclasses.replace(
                note,
                start_tick=note.start_tick // factor,
                duration_ticks=max(MIN_TICKS, note.duration_ticks // factor),
            )
            for note in measure.notes
        ]
        measures.append(
            dataclasses.replace(
                measure,
                notes=notes,
                start_tick=measure.start_tick // factor,
                duration_ticks=max(MIN_TICKS, measure.duration_ticks // factor),
            )
        )
    return dataclasses.replace(phrase, measures=measures)