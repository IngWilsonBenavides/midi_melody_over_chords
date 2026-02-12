from __future__ import annotations

from dictados.domain.chord import Chord, ChordQuality
from dictados.domain.scale import Scale

_ROMAN_TO_DEGREE = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
}


def parse_roman_numeral(numeral: str) -> tuple[int, ChordQuality]:
    raw = numeral.strip()
    diminished = raw.endswith("°") or raw.endswith("o")
    if diminished:
        raw = raw[:-1]
    key = raw.lower()
    if key not in _ROMAN_TO_DEGREE:
        raise ValueError(f"Invalid roman numeral: {numeral}")
    degree = _ROMAN_TO_DEGREE[key]
    if diminished:
        quality = ChordQuality.DIMINISHED
    else:
        quality = ChordQuality.MAJOR if raw.isupper() else ChordQuality.MINOR
    return degree, quality


class ProgressionGenerator:
    def expand_progression(
        self,
        numerals: list[str],
        groups: int,
        scale: Scale,
    ) -> list[Chord]:
        chords: list[Chord] = []
        for _ in range(groups):
            for numeral in numerals:
                degree, quality = parse_roman_numeral(numeral)
                chords.append(scale.chord_from_degree(degree, quality))
        return chords
