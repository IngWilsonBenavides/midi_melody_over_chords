from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dictados.domain.pitch import Pitch


@dataclass(frozen=True)
class Note:
    pitch: Optional[Pitch]  # None for rest, ghost, or muted notes
    start_tick: int
    duration_ticks: int
    velocity: int = 100
    note_type: str = "normal"  # "normal", "rest", "ghost", "muted"

    @property
    def end_tick(self) -> int:
        return self.start_tick + self.duration_ticks

    @property
    def is_audible(self) -> bool:
        """Returns True if note produces sound."""
        return self.note_type == "normal" and self.pitch is not None
