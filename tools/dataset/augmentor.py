"""Augmentor — transposition and tempo jitter for dataset augmentation.

For each training example this module produces up to 14 variants:

- **Transposition × 12**: shift the chord root by −5 to +6 semitones.  The
  intervals in the melody tokens are unchanged (they are root-relative), but
  we verify that the *absolute* MIDI pitches reconstructed from root+interval
  stay within C3–C6.  Variants that push >20% of notes out of range are
  discarded.
- **Tempo jitter × 2**: multiply ``tempo_bpm`` by 0.97 and 1.03.

Usage::

    from tools.dataset.augmentor import augment_example

    variants = augment_example(example)
    # variants includes the original plus up to 13 transpositions × 3 tempo factors
"""
from __future__ import annotations

import copy
from typing import Any

from tools.dataset.normalizer import RANGE_LOW, RANGE_HIGH

# Semitone shifts to try for transposition augmentation.
_TRANSPOSE_SHIFTS: list[int] = list(range(-5, 7))  # −5 … +6 (skipping 0 for original)

# Tempo scaling factors.
_TEMPO_FACTORS: list[float] = [0.97, 1.0, 1.03]

# Maximum fraction of out-of-range notes allowed in an augmented example.
_MAX_OUT_OF_RANGE: float = 0.20

# C major chord roots by pitch class (for shifting chord symbols).
_PC_TO_NAME: list[str] = ["C", "C#", "D", "D#", "E", "F",
                           "F#", "G", "G#", "A", "A#", "B"]

_ROOT_PC: dict[str, int] = {
    "C": 0,  "C#": 1, "Db": 1, "D": 2,  "D#": 3, "Eb": 3,
    "E": 4,  "F": 5,  "F#": 6, "Gb": 6, "G": 7,  "G#": 8,
    "Ab": 8, "A": 9,  "A#": 10,"Bb": 10,"B": 11,
}

_QUALITY_SUFFIXES: tuple[str, ...] = (
    "maj7", "m7b5", "dim7", "dom7", "maj", "min",
    "m7",   "7",    "m",    "",
)


def _transpose_chord(symbol: str, semitones: int) -> str:
    """Transpose a chord symbol by *semitones* semitones."""
    if not symbol or symbol == "?":
        return symbol
    # Parse root and quality suffix.
    root = None
    suffix = ""
    for length in (3, 2, 1):
        candidate = symbol[:length]
        if candidate in _ROOT_PC:
            root = candidate
            suffix = symbol[length:]
            break
    if root is None:
        return symbol
    new_pc = (_ROOT_PC[root] + semitones) % 12
    return _PC_TO_NAME[new_pc] + suffix


def _reconstruct_midi(interval: int, chord_symbol: str, octave_hint: int = 5) -> int:
    """Reconstruct an absolute MIDI number from an interval and chord root.

    Places the chord root at MIDI ``root_pc + 12 * octave_hint``
    (e.g. ``octave_hint=5`` → root starts at MIDI 60, i.e. C4 / middle C),
    then shifts the result by octaves to fit within C3–C6 (MIDI 48–84).
    """
    root_name = None
    for length in (3, 2, 1):
        candidate = chord_symbol[:length] if chord_symbol else ""
        if candidate in _ROOT_PC:
            root_name = candidate
            break
    if root_name is None:
        return 60  # fallback
    root_pc = _ROOT_PC[root_name]
    # Place root in octave 5.
    root_midi = root_pc + 12 * octave_hint
    midi = root_midi + interval
    # Shift by octaves to fit range.
    while midi < RANGE_LOW:
        midi += 12
    while midi > RANGE_HIGH:
        midi -= 12
    return midi


def _count_out_of_range(
    tokens: list[dict[str, Any]],
    context_chords: list[str],
    window_bars: int,
) -> int:
    """Count tokens whose reconstructed MIDI note is outside C3–C6."""
    out = 0
    n_bars = max(len(context_chords), window_bars)
    for i, tok in enumerate(tokens):
        if tok["interval"] is None:
            continue
        bar_idx = min(i * window_bars // max(len(tokens), 1), n_bars - 1)
        chord = context_chords[bar_idx] if bar_idx < len(context_chords) else "?"
        midi = _reconstruct_midi(tok["interval"], chord)
        if midi < RANGE_LOW or midi > RANGE_HIGH:
            out += 1
    return out


def augment_example(example: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate all augmented variants of a single training example.

    The original example (shift=0, factor=1.0) is always included first.

    Args:
        example: A tokenised training example (output of
                 :func:`tools.dataset.tokenizer.tokenise_segment`).

    Returns:
        List of example dicts (including the original).
    """
    results: list[dict[str, Any]] = []
    melody = example["melody"]
    context_chords = example.get("context_chords", [])
    window_bars = example["meta"].get("window_bars", 4)
    base_tempo = example["meta"].get("tempo_bpm", 120.0)

    for shift in _TRANSPOSE_SHIFTS:
        # Transpose chord symbols.
        new_chords = [_transpose_chord(c, shift) for c in context_chords]

        # Check range feasibility (melody intervals are unchanged; only root shifts).
        out = _count_out_of_range(melody, new_chords, window_bars)
        total = max(len(melody), 1)
        if out / total > _MAX_OUT_OF_RANGE and shift != 0:
            continue

        for factor in _TEMPO_FACTORS:
            new_example = copy.deepcopy(example)
            new_example["context_chords"] = new_chords
            new_example["meta"]["tempo_bpm"] = round(base_tempo * factor, 2)
            new_example["meta"]["augmentation"] = {
                "transpose_semitones": shift,
                "tempo_factor": round(factor, 4),
            }
            results.append(new_example)

    # Always ensure the identity transform (shift=0, factor=1.0) is present.
    identity_present = any(
        v["meta"]["augmentation"]["transpose_semitones"] == 0
        and v["meta"]["augmentation"]["tempo_factor"] == 1.0
        for v in results
    )
    if not identity_present:
        orig = copy.deepcopy(example)
        orig["meta"]["augmentation"] = {"transpose_semitones": 0, "tempo_factor": 1.0}
        results.insert(0, orig)

    return results
