from __future__ import annotations

from dictados.config import DictationSpec


def validate_spec(spec: DictationSpec) -> list[str]:
    errors: list[str] = []
    if not spec.progression:
        errors.append("progression must not be empty")
    if spec.groups < 1:
        errors.append("groups must be >= 1")
    if len(spec.sequence) != 4 or sorted(spec.sequence) != ["1", "2", "3", "4"]:
        errors.append("sequence must be a permutation of 1234")
    low, high = spec.range
    if low < 41 or high > 81:
        errors.append("range must be within 41-81")
    if low > high:
        errors.append("range low must be <= high")
    return errors
