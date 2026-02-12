from __future__ import annotations

from dictados.domain.pitch import Pitch


class SequenceApplicator:
    @staticmethod
    def apply_pattern(notes: list[Pitch], pattern: str) -> list[Pitch]:
        if len(notes) != 4:
            raise ValueError("Sequence expects 4 notes")
        if len(pattern) != 4 or sorted(pattern) != ["1", "2", "3", "4"]:
            raise ValueError("Pattern must be a permutation of 1234")
        indices = [int(c) - 1 for c in pattern]
        return [notes[i] for i in indices]
