from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, Field, field_validator


class DictationSpec(BaseModel):
    key: str
    progression: list[str]
    groups: int
    subdivision: str
    sequence: str
    range: Tuple[int, int] = Field(alias="range")
    tempo: int = 100
    ppqn: int = 480
    time_signature: str = "4/4"
    program: int = 30

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, value: str) -> str:
        if len(value) != 4 or sorted(value) != ["1", "2", "3", "4"]:
            raise ValueError("sequence must be a permutation of 1234")
        return value

    @field_validator("groups")
    @classmethod
    def validate_groups(cls, value: int) -> int:
        if value < 1:
            raise ValueError("groups must be >= 1")
        return value

    @field_validator("range")
    @classmethod
    def validate_range(cls, value: Tuple[int, int]) -> Tuple[int, int]:
        low, high = value
        if low > high:
            raise ValueError("range low must be <= high")
        if low < 41 or high > 81:
            raise ValueError("range must be within 41-81")
        return value

    @field_validator("time_signature")
    @classmethod
    def validate_time_signature(cls, value: str) -> str:
        parts = value.split("/")
        if len(parts) != 2:
            raise ValueError("time_signature must be like 4/4")
        num, den = parts
        if not num.isdigit() or not den.isdigit():
            raise ValueError("time_signature must be numeric")
        return value
