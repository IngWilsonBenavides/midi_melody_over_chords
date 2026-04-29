# Dataset Specification — Melodic Improviser Training Data

## Overview

This document defines the format, vocabulary, and metadata schema for the
multi-style monophonic melody dataset used to train the musical improviser.

**Format chosen: Sequence of interval+duration tuples (Option C)**  
Each training example is a JSON object containing a chord context window and a
melody sequence expressed as relative intervals — making every example
transposition-invariant by construction.

---

## File layout

| Path | Content |
|------|---------|
| `data/raw/` | Original MIDI files (not committed — see `data/README.md`) |
| `data/processed/` | Extracted, normalised, tokenised examples in `.jsonl` format |
| `data/splits/train.jsonl` | 80% of examples (split by source song) |
| `data/splits/val.jsonl` | 10% of examples |
| `data/splits/test.jsonl` | 10% of examples |

Each `.jsonl` file contains one JSON object per line.

---

## Example schema

```json
{
  "source": "lakh/some_file.mid",
  "context_chords": ["Am", "C", "Dm", "G7"],
  "melody": [
    {"interval": 0,  "dur_bin": 4, "vel_bin": 2, "pos_16th": 0},
    {"interval": 2,  "dur_bin": 2, "vel_bin": 2, "pos_16th": 4},
    {"interval": 3,  "dur_bin": 2, "vel_bin": 3, "pos_16th": 6},
    {"interval": 5,  "dur_bin": 4, "vel_bin": 3, "pos_16th": 8},
    {"interval": -1, "dur_bin": 2, "vel_bin": 1, "pos_16th": 12}
  ],
  "meta": {
    "tempo_bpm": 120,
    "time_sig": "4/4",
    "key": "Am",
    "style": "jazz",
    "difficulty": 2,
    "window_bars": 4,
    "ppqn_original": 480,
    "augmentation": {"transpose_semitones": 0, "tempo_factor": 1.0}
  }
}
```

### Field definitions

#### Top-level

| Field | Type | Description |
|-------|------|-------------|
| `source` | `str` | Relative path of the source MIDI file within `data/raw/` |
| `context_chords` | `list[str]` | Chord symbol per bar in the window, e.g. `["Am", "G"]` |
| `melody` | `list[NoteToken]` | Sequence of note tokens (see below) |
| `meta` | `Metadata` | Tempo, key, style, and processing metadata |

#### NoteToken

Each note in the melody is a dict with four integer fields:

| Field | Range | Description |
|-------|-------|-------------|
| `interval` | −24 … +24 | Semitones from the **root of the current bar's chord** |
| `dur_bin` | 0 … 7 | Duration bin (see table below) |
| `vel_bin` | 0 … 4 | Velocity bin (see table below) |
| `pos_16th` | 0 … 15 | Note onset position within the bar, in 16th-note units (4/4) |

A **rest** is encoded as a NoteToken with `interval = null`.

#### Metadata

| Field | Type | Description |
|-------|------|-------------|
| `tempo_bpm` | `float` | Tempo in beats per minute at the start of the window |
| `time_sig` | `str` | Time signature, e.g. `"4/4"`, `"3/4"` |
| `key` | `str \| null` | Inferred key, e.g. `"Am"`, `"C"`. `null` if unknown |
| `style` | `str \| null` | Genre tag, e.g. `"jazz"`, `"blues"`, `"rock"`. `null` if unknown |
| `difficulty` | `int` | 0–4 difficulty rating (see table below) |
| `window_bars` | `int` | Number of bars in this example |
| `ppqn_original` | `int` | PPQN of the source MIDI |
| `augmentation` | `dict` | Transpose amount and tempo scaling applied to this example |

---

## Vocabulary tables

### Duration bins (`dur_bin`)

| Value | Name | Duration | Ticks (at PPQN 96) |
|-------|------|----------|--------------------|
| 0 | 32nd note | T/8 | 12 (< 18) |
| 1 | 16th note | T/4 | 24 (18–35) |
| 2 | 8th note | T/2 | 48 (36–59) |
| 3 | Dotted 8th | 3T/4 | 72 (60–83) |
| 4 | Quarter note | T | 96 (84–119) |
| 5 | Dotted quarter | 3T/2 | 144 (120–167) |
| 6 | Half note | 2T | 192 (168–287) |
| 7 | Whole / longer | ≥3T | ≥288 |

*T = one quarter note. Notes longer than a half are either kept as bin 7 or
split into multiple tokens.*

### Velocity bins (`vel_bin`)

| Value | Name | MIDI velocity range |
|-------|------|---------------------|
| 0 | pp (pianissimo) | 1–31 |
| 1 | p (piano) | 32–63 |
| 2 | mf (mezzo-forte) | 64–95 |
| 3 | f (forte) | 96–111 |
| 4 | ff (fortissimo) | 112–127 |

### Difficulty levels

| Value | Description |
|-------|-------------|
| 0 | Very easy — slow, stepwise, few notes per bar |
| 1 | Easy — mostly stepwise, occasional small skips |
| 2 | Intermediate — some leaps, moderate density |
| 3 | Advanced — frequent leaps, high density, chromatic |
| 4 | Expert — very high density, wide intervals, complex rhythm |

Difficulty is computed automatically from: notes-per-bar density, average
interval size, and proportion of chromatic notes.

---

## Normalisation pipeline

1. **PPQN normalisation** — re-quantise all ticks to an internal grid of
   `ppqn_norm = 96` ticks per quarter note (one 16th note = 24 ticks).
2. **Range filter** — keep only notes in MIDI range 48–84 (C3–C6). Notes
   outside this range are shifted by octaves; if still out of range they are
   discarded.
3. **Velocity binning** — map raw MIDI velocity (1–127) to `vel_bin` (0–4).
4. **Quantisation** — snap onsets and durations to the nearest 16th-note
   grid point. A ±10% tolerance is applied before snapping (flexible
   quantisation to preserve some swing feel in the *interval* representation).
5. **Duration binning** — map quantised durations to `dur_bin` (0–7).
6. **Chord detection** — if the source has a separate chord track or an
   accompanying track, pitch-class sets are matched against chord templates.
   Otherwise `context_chords` is left empty or set to `["?"]`.
7. **Key inference** — Krumhansl–Schmuckler key profiles are applied to the
   pitch-class histogram of the window.

---

## Augmentation

Each original example is augmented to produce up to **14 variants**:

- **Transposition** × 12: shift by −5 to +6 semitones, keeping notes inside
  C3–C6 (MIDI 48–84). Variants that push more than 20% of notes out of range
  are discarded.
- **Tempo jitter** × 2: multiply all tick durations by 0.97 and 1.03.
  Only tick positions are affected; `tempo_bpm` in metadata is updated.

The `augmentation` dict in metadata records the exact transformation applied
so experiments can filter or weight augmented vs. original examples.

---

## Train/val/test split

Splits are made **by source file** (not by example) to prevent data leakage:

- Shuffle source files with a fixed seed (`--seed`).
- Assign 80% of files to train, 10% to val, 10% to test.
- All augmented variants of a given file go into the same split.

---

## Licensing

All source MIDI files must be legally usable for research and derivative works.
See `data/README.md` for the approved source list with license details.
Processed examples inherit the license of their source.
