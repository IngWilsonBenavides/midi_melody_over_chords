"""BaseImproModel — abstract base class for all melodic improvisation models.

Every concrete model (n-gram, GRU, Transformer, …) must implement:

- ``fit(train_path)``  — train from a JSONL dataset split.
- ``sample_bar(chord_symbol, beat_group, prev_interval, prev_dur_bin, …)``
  — sample the next ``(interval, dur_bin)`` token.

The slot for future neural models is deliberately left open: swap out
``ngram.py`` for ``gru.py`` while keeping the same interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseImproModel(ABC):
    """Abstract base for data-driven melodic improvisation models."""

    # ── Training ───────────────────────────────────────────────────────────────

    @abstractmethod
    def fit(self, train_path: Path) -> None:
        """Train (or fit) the model from *train_path* (JSONL dataset split)."""

    # ── Sampling ───────────────────────────────────────────────────────────────

    @abstractmethod
    def sample_next(
        self,
        *,
        chord_quality: str,
        beat_group: int,
        prev_interval_bucket: Optional[int],
        prev_dur_bin: Optional[int],
        temperature: float = 1.0,
        style_tag: str = "neutral",
    ) -> tuple[Optional[int], int]:
        """Sample the next ``(interval, dur_bin)`` given context.

        Args:
            chord_quality:        One of ``"m"``, ``"M"``, ``"7"``, ``"dim"``, ``"?"``.
            beat_group:           0–3 (quarter-note group within the bar).
            prev_interval_bucket: Quantised previous interval (or None at bar start).
            prev_dur_bin:         Previous duration bin 0–7 (or None at bar start).
            temperature:          Sampling temperature; >1 → more random, <1 → greedier.
            style_tag:            Style conditioning tag (currently always ``"neutral"``).

        Returns:
            ``(interval, dur_bin)`` where ``interval`` is ``None`` for a rest,
            otherwise a semitone offset relative to the chord root (−6 to +6).
        """

    # ── Persistence ────────────────────────────────────────────────────────────

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist the trained model to *path*."""

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> "BaseImproModel":
        """Load a persisted model from *path*."""
