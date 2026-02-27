from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


class MeasureSpec(BaseModel):
    """Specification for a single measure with melody."""
    compas: int
    notes: list[str]  # e.g. ['D', 'G', 'A', 'B', 'C']
    rhythm: list[str]  # e.g. ['q', 'e', 'e', 'e', 'e']


class DictationSpec(BaseModel):
    """Specification for dictation generation.
    
    Can be in two modes:
    1. Generated: progression + groups + sequence + subdivision
    2. Specific: melody (list of measures with explicit notes and rhythms)
    """
    key: str
    time_signature: str = "4/4"
    tempo_bpm: int = 100
    ppqn: int = 480
    program: int = 30
    
    # Generated mode (original)
    progression: Optional[list[str]] = None
    groups: Optional[int] = None
    subdivision: Optional[str] = None
    sequence: Optional[str] = None
    range: Optional[Tuple[int, int]] = Field(default=None, alias="range")
    tempo: Optional[int] = None  # kept for backward compatibility
    
    # Specific melody mode (new)
    melody: Optional[list[MeasureSpec]] = None

    @model_validator(mode="after")
    def validate_mode(self):
        """Ensure either generated or specific melody mode is provided."""
        if self.melody is not None:
            # Specific melody mode
            if self.progression is not None:
                raise ValueError("Cannot specify both 'melody' and 'progression'")
        else:
            # Generated mode
            if self.progression is None or self.groups is None:
                raise ValueError("Must specify either 'melody' or 'progression'+'groups'")
            if self.subdivision is None or self.sequence is None:
                raise ValueError("Generated mode requires 'subdivision' and 'sequence'")
        return self

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) != 4 or sorted(value) != ["1", "2", "3", "4"]:
            raise ValueError("sequence must be a permutation of 1234")
        return value

    @field_validator("groups")
    @classmethod
    def validate_groups(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1:
            raise ValueError("groups must be >= 1")
        return value

    @field_validator("range")
    @classmethod
    def validate_range(cls, value: Tuple[int, int] | None) -> Tuple[int, int] | None:
        if value is None:
            return None
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

    @field_validator("melody")
    @classmethod
    def validate_melody(cls, value: list[MeasureSpec] | None) -> list[MeasureSpec] | None:
        if value is None:
            return None
        if len(value) == 0:
            raise ValueError("melody must have at least one measure")
        for measure in value:
            if len(measure.notes) != len(measure.rhythm):
                raise ValueError(
                    f"Measure {measure.compas}: number of notes ({len(measure.notes)}) "
                    f"must match number of rhythms ({len(measure.rhythm)})"
                )
        return value
