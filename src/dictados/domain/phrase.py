from __future__ import annotations

from dataclasses import dataclass

from dictados.domain.note import Note
from dictados.domain.chord import Chord


@dataclass
class Measure:
    notes: list[Note]
    chord: Chord
    start_tick: int
    duration_ticks: int


@dataclass
class Phrase:
    measures: list[Measure]
    ppqn: int = 480
