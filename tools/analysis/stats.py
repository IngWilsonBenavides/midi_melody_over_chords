"""Dataset statistics — compute distribution metrics from split JSONL files.

Usage::

    from tools.analysis.stats import compute_stats

    stats = compute_stats(Path("data/splits/train.jsonl"))
    print(stats)
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    examples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return examples


def compute_stats(jsonl_path: Path) -> dict[str, Any]:
    """Compute dataset statistics from a JSONL file.

    Returns a dict with keys covering:
    - example / token counts
    - interval distribution
    - dur_bin distribution
    - vel_bin distribution
    - notes per bar
    - rhythmic density
    - pitch range
    - style breakdown
    - difficulty distribution
    - tempo distribution
    """
    examples = _load_jsonl(jsonl_path)
    if not examples:
        return {"n_examples": 0}

    # Collect raw data.
    intervals: list[int] = []
    dur_bins: list[int] = []
    vel_bins: list[int] = []
    notes_per_bar_list: list[float] = []
    styles: list[str] = []
    difficulties: list[int] = []
    tempos: list[float] = []
    pos_16ths: list[int] = []

    for ex in examples:
        melody = ex.get("melody", [])
        window_bars = ex.get("meta", {}).get("window_bars", 4)
        style = ex.get("meta", {}).get("style")
        difficulty = ex.get("meta", {}).get("difficulty")
        tempo = ex.get("meta", {}).get("tempo_bpm")

        if melody:
            notes_per_bar_list.append(len(melody) / max(window_bars, 1))

        for tok in melody:
            iv = tok.get("interval")
            if iv is not None:
                intervals.append(iv)
            db = tok.get("dur_bin")
            if db is not None:
                dur_bins.append(db)
            vb = tok.get("vel_bin")
            if vb is not None:
                vel_bins.append(vb)
            p16 = tok.get("pos_16th")
            if p16 is not None:
                pos_16ths.append(p16)

        if style:
            styles.append(style)
        if difficulty is not None:
            difficulties.append(difficulty)
        if tempo is not None:
            tempos.append(tempo)

    n_tokens = len(intervals)

    stats: dict[str, Any] = {
        "n_examples": len(examples),
        "n_tokens": n_tokens,
        "n_sources": len({ex["source"] for ex in examples}),
    }

    # Interval distribution.
    if intervals:
        iv_counter = Counter(intervals)
        stats["interval_distribution"] = {
            str(k): v for k, v in sorted(iv_counter.items())
        }
        stats["interval_mean"] = round(sum(intervals) / len(intervals), 3)
        stats["interval_abs_mean"] = round(
            sum(abs(i) for i in intervals) / len(intervals), 3
        )
        stats["interval_std"] = round(
            math.sqrt(
                sum((i - stats["interval_mean"]) ** 2 for i in intervals) / len(intervals)
            ),
            3,
        )
        stats["interval_chromatic_fraction"] = round(
            sum(1 for i in intervals if abs(i) % 2 != 0) / len(intervals), 3
        )

    # Duration bin distribution.
    _DUR_NAMES = [
        "32nd", "16th", "8th", "dotted_8th",
        "quarter", "dotted_quarter", "half", "whole_or_longer",
    ]
    if dur_bins:
        db_counter = Counter(dur_bins)
        stats["dur_bin_distribution"] = {
            _DUR_NAMES[k]: v for k, v in sorted(db_counter.items()) if 0 <= k < len(_DUR_NAMES)
        }

    # Velocity bin distribution.
    _VEL_NAMES = ["pp", "p", "mf", "f", "ff"]
    if vel_bins:
        vb_counter = Counter(vel_bins)
        stats["vel_bin_distribution"] = {
            _VEL_NAMES[k]: v for k, v in sorted(vb_counter.items()) if 0 <= k < len(_VEL_NAMES)
        }

    # Notes per bar.
    if notes_per_bar_list:
        stats["notes_per_bar_mean"] = round(
            sum(notes_per_bar_list) / len(notes_per_bar_list), 3
        )
        stats["notes_per_bar_min"] = round(min(notes_per_bar_list), 3)
        stats["notes_per_bar_max"] = round(max(notes_per_bar_list), 3)

    # Rhythmic density: average unique pos_16th values per example.
    if pos_16ths and examples:
        ex_pos_counts = []
        start = 0
        for ex in examples:
            n = len(ex.get("melody", []))
            ex_pos = pos_16ths[start: start + n]
            start += n
            if ex_pos:
                ex_pos_counts.append(len(set(ex_pos)))
        if ex_pos_counts:
            stats["rhythmic_density_mean"] = round(
                sum(ex_pos_counts) / len(ex_pos_counts), 3
            )

    # Style breakdown.
    if styles:
        stats["style_distribution"] = {
            k: v for k, v in sorted(Counter(styles).items(), key=lambda x: -x[1])
        }

    # Difficulty distribution.
    if difficulties:
        stats["difficulty_distribution"] = {
            str(k): v for k, v in sorted(Counter(difficulties).items())
        }

    # Tempo statistics.
    if tempos:
        stats["tempo_mean_bpm"] = round(sum(tempos) / len(tempos), 2)
        stats["tempo_min_bpm"] = round(min(tempos), 2)
        stats["tempo_max_bpm"] = round(max(tempos), 2)

    return stats


def compute_all_splits(splits_dir: Path) -> dict[str, dict[str, Any]]:
    """Compute stats for train, val, and test splits.

    Returns a dict with keys ``"train"``, ``"val"``, ``"test"`` (if files exist).
    """
    result: dict[str, dict[str, Any]] = {}
    for split_name in ("train", "val", "test"):
        path = splits_dir / f"{split_name}.jsonl"
        if path.exists():
            result[split_name] = compute_stats(path)
    return result
