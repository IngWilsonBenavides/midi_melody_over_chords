"""ChordConditionedNGram — chord- and position-aware Markov melody model.

The model learns the joint distribution:

    P(interval, dur_bin | prev_interval_bucket, prev_dur_bin,
                          chord_quality_tag, beat_group)

State tuple (context key):
    (prev_interval_bucket, prev_dur_bin, chord_quality_tag, beat_group)

Where:
    prev_interval_bucket: quantised previous interval (step=2), or "R" for REST,
                          or None (encoded as "S" for start-of-bar).
    prev_dur_bin:         previous duration bin 0–7, or None (encoded as -1).
    chord_quality_tag:    "m" | "M" | "7" | "dim" | "?"
    beat_group:           0–3 (quarter-note group within bar)

Add-alpha (Laplace) smoothing prevents zero-probability transitions.

Sampling uses temperature scaling on the log-probability distribution.

TODO: replace this file with ``gru.py`` for a neural sequence model
      while keeping the BaseImproModel interface unchanged.
"""
from __future__ import annotations

import json
import math
import pickle
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from ml.model.base import BaseImproModel
from ml.model.vocab import (
    bucket_interval,
    chord_quality_tag,
    pos_16th_to_beat_group,
)

# Sentinel values for encoding None in the state tuple (must be hashable).
_START_INTERVAL = "S"   # start-of-bar (no previous note)
_REST_INTERVAL  = "R"   # previous token was a rest
_START_DUR      = -1    # no previous duration


class ChordConditionedNGram(BaseImproModel):
    """Chord- and position-conditioned bigram Markov model.

    Args:
        order:       Context window length (1 = unigram; currently only 1 is
                     used for the melody context, but chord + position context
                     is always included — effectively a conditioned bigram).
        alpha:       Add-alpha smoothing constant.
        rest_prob_boost: Extra probability mass added to REST tokens to encourage
                     musical breathing.  Set to 0 to rely entirely on data.
        seed:        Random seed for reproducibility.
    """

    def __init__(
        self,
        order: int = 1,
        alpha: float = 0.5,
        rest_prob_boost: float = 0.05,
        seed: Optional[int] = None,
    ) -> None:
        self.order = order
        self.alpha = alpha
        self.rest_prob_boost = rest_prob_boost
        self.seed = seed
        self._rng = random.Random(seed)

        # counts[state_key] → Counter of (interval_or_None, dur_bin) outcomes.
        self._counts: dict[tuple, Counter] = defaultdict(Counter)
        # vocabulary of outcomes seen during training.
        self._vocab: set[tuple] = set()
        # per-(quality, beat_group) velocity distribution.
        self._vel_counts: dict[tuple, Counter] = defaultdict(Counter)

    # ── Training ───────────────────────────────────────────────────────────────

    def fit(self, train_path: Path) -> None:
        """Fit model from a JSONL dataset split."""
        self._counts.clear()
        self._vocab.clear()
        self._vel_counts.clear()

        with train_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._process_example(ex)

    def _process_example(self, ex: dict) -> None:
        """Accumulate counts from one dataset example."""
        tokens: list[dict] = ex.get("melody", [])
        if not tokens:
            return

        chords: list[str] = ex.get("context_chords", [])
        style_tag: str = ex.get("meta", {}).get("style_tag", "neutral")  # noqa: F841

        # Determine chord quality from first chord in context.
        q_tag = chord_quality_tag(chords[0]) if chords else "?"

        prev_ibucket: object = _START_INTERVAL
        prev_dur_bin: int = _START_DUR

        for tok in tokens:
            interval: Optional[int] = tok.get("interval")
            dur_bin: int = int(tok.get("dur_bin", 2))
            vel_bin: int = int(tok.get("vel_bin", 2))
            pos_16th: int = int(tok.get("pos_16th", 0))

            beat_group = pos_16th_to_beat_group(pos_16th)
            ibucket = _bucket_encode(bucket_interval(interval))

            state = (prev_ibucket, prev_dur_bin, q_tag, beat_group)
            outcome = (interval, dur_bin)

            self._counts[state][outcome] += 1
            self._vocab.add(outcome)
            self._vel_counts[(q_tag, beat_group)][vel_bin] += 1

            prev_ibucket = ibucket
            prev_dur_bin = dur_bin

    # ── Sampling ───────────────────────────────────────────────────────────────

    def sample_next(
        self,
        *,
        chord_quality: str,
        beat_group: int,
        prev_interval_bucket: Optional[int],
        prev_dur_bin: Optional[int],
        temperature: float = 1.0,
        style_tag: str = "neutral",  # slot prepared for future conditioning
    ) -> tuple[Optional[int], int]:
        """Sample the next ``(interval, dur_bin)`` given context."""
        prev_ibucket_enc = _bucket_encode(prev_interval_bucket)
        prev_dur_enc = prev_dur_bin if prev_dur_bin is not None else _START_DUR

        state = (prev_ibucket_enc, prev_dur_enc, chord_quality, beat_group)
        counter = self._counts.get(state, Counter())

        # Fall back to chord+beat_group marginal if state unseen.
        if not counter:
            counter = _merge_counters(
                c for (_, _, q, bg), c in self._counts.items()
                if q == chord_quality and bg == beat_group
            )
        # Final fallback: global distribution.
        if not counter:
            counter = _merge_counters(self._counts.values())
        # Emergency: uniform over all vocab tokens.
        if not counter or not self._vocab:
            fallback_vocab = list(self._vocab) or [(0, 2)]
            return self._rng.choice(fallback_vocab)

        outcomes = list(counter.keys())
        raw_counts = [counter[o] for o in outcomes]

        # Apply rest probability boost.
        if self.rest_prob_boost > 0:
            boosted = []
            for i, (iv, _db) in enumerate(outcomes):
                boost = self.rest_prob_boost if iv is None else 0.0
                boosted.append(raw_counts[i] + boost * sum(raw_counts))
            raw_counts = boosted

        # Temperature-scaled sampling.
        chosen = _temperature_sample(outcomes, raw_counts, temperature, self._rng)
        return chosen  # type: ignore[return-value]

    def sample_velocity(
        self,
        chord_quality: str,
        beat_group: int,
        temperature: float = 1.0,
    ) -> int:
        """Sample a vel_bin (0–4) for the given context."""
        counter = self._vel_counts.get((chord_quality, beat_group), Counter())
        if not counter:
            counter = _merge_counters(
                c for (q, _), c in self._vel_counts.items() if q == chord_quality
            )
        if not counter:
            return 2  # default: mf
        vel_bins = list(counter.keys())
        counts = [counter[v] for v in vel_bins]
        return _temperature_sample(vel_bins, counts, temperature, self._rng)  # type: ignore[return-value]

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """Pickle the model to *path*."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "order": self.order,
            "alpha": self.alpha,
            "rest_prob_boost": self.rest_prob_boost,
            "seed": self.seed,
            "counts": dict(self._counts),
            "vocab": self._vocab,
            "vel_counts": dict(self._vel_counts),
        }
        with path.open("wb") as fh:
            pickle.dump(data, fh, protocol=4)

    @classmethod
    def load(cls, path: Path) -> "ChordConditionedNGram":
        """Load a pickled model from *path*."""
        with path.open("rb") as fh:
            data = pickle.load(fh)
        obj = cls(
            order=data["order"],
            alpha=data["alpha"],
            rest_prob_boost=data.get("rest_prob_boost", 0.05),
            seed=data.get("seed"),
        )
        obj._counts = defaultdict(Counter, data["counts"])
        obj._vocab = data["vocab"]
        obj._vel_counts = defaultdict(Counter, data["vel_counts"])
        return obj

    # ── Diagnostics ────────────────────────────────────────────────────────────

    def vocab_size(self) -> int:
        return len(self._vocab)

    def state_count(self) -> int:
        return len(self._counts)

    def perplexity(self, val_path: Path) -> float:
        """Compute per-token perplexity on a validation JSONL split."""
        total_log = 0.0
        n_tokens = 0
        vocab_size = max(len(self._vocab), 1)

        with val_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                except json.JSONDecodeError:
                    continue

                tokens = ex.get("melody", [])
                chords = ex.get("context_chords", [])
                q_tag = chord_quality_tag(chords[0]) if chords else "?"
                prev_ibucket: object = _START_INTERVAL
                prev_dur = _START_DUR

                for tok in tokens:
                    interval = tok.get("interval")
                    dur_bin = int(tok.get("dur_bin", 2))
                    pos_16th = int(tok.get("pos_16th", 0))
                    beat_group = pos_16th_to_beat_group(pos_16th)
                    ibucket = _bucket_encode(bucket_interval(interval))

                    state = (prev_ibucket, prev_dur, q_tag, beat_group)
                    counter = self._counts.get(state, Counter())
                    if not counter:
                        counter = _merge_counters(
                            c for (_, _, q, bg), c in self._counts.items()
                            if q == q_tag and bg == beat_group
                        )
                    outcome = (interval, dur_bin)
                    total = sum(counter.values())
                    count = counter.get(outcome, 0)
                    prob = (count + self.alpha) / (total + self.alpha * vocab_size)
                    total_log += math.log(max(prob, 1e-15))
                    n_tokens += 1

                    prev_ibucket = ibucket
                    prev_dur = dur_bin

        if n_tokens == 0:
            return float("inf")
        return math.exp(-total_log / n_tokens)


# ── Private helpers ────────────────────────────────────────────────────────────

def _bucket_encode(bucket: Optional[int]) -> object:
    """Encode a (possibly None) interval bucket into a hashable sentinel."""
    if bucket is None:
        return _REST_INTERVAL
    return bucket


def _merge_counters(counters) -> Counter:
    """Merge an iterable of Counters into one."""
    merged: Counter = Counter()
    for c in counters:
        merged.update(c)
    return merged


def _temperature_sample(
    outcomes: list,
    raw_counts: list[float],
    temperature: float,
    rng: random.Random,
) -> object:
    """Sample from *outcomes* weighted by *raw_counts* with temperature."""
    if temperature <= 0:
        # Greedy: pick argmax.
        return outcomes[raw_counts.index(max(raw_counts))]

    # Log-domain temperature scaling to avoid overflow.
    log_counts = [math.log(max(c, 1e-9)) / temperature for c in raw_counts]
    max_log = max(log_counts)
    weights = [math.exp(lc - max_log) for lc in log_counts]
    total = sum(weights)
    weights = [w / total for w in weights]

    r = rng.random()
    cumulative = 0.0
    for outcome, w in zip(outcomes, weights):
        cumulative += w
        if r <= cumulative:
            return outcome
    return outcomes[-1]
