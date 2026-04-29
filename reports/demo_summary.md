# Demo Summary — ML Melodic Improviser
**Progression:** Am Am Em Em Am Am Dm Dm  **Tempo:** 100.0 BPM  **Model:** Chord-Conditioned N-gram Markov
---
## How to listen
Open any of the files in `outputs/` with a MIDI player:
- **macOS**: GarageBand, QuickTime Player, or `afplay` (for MP3 exports)
- **Windows**: Windows Media Player, MuseScore
- **Linux**: TiMidity++, FluidSynth, MuseScore
- **Online**: [midi.city](https://midi.city), [BeepBox](https://www.beepbox.co)

## How to reproduce
```bash
# 1. Build dataset (if not already done):
make dataset

# 2. Train the model:
make train

# 3. Generate demo files + this report:
make demo
```

---
## Results

| File | Type | Description |
|------|------|-------------|
| `before.mid` | Rule-based (ImproEngine) | Existing lick/arpeggio/scale-walk strategy engine — no ML |
| `after_seed_42.mid` | ML (N-gram, seed=42) | Chord-conditioned Markov model, temperature=1.0 |
| `after_seed_43.mid` | ML (N-gram, seed=43) | Chord-conditioned Markov model, temperature=1.0 |
| `after_seed_44.mid` | ML (N-gram, seed=44) | Chord-conditioned Markov model, temperature=1.0 |
| `after_seed_45.mid` | ML (N-gram, seed=45) | Chord-conditioned Markov model, temperature=1.0 |
| `after_seed_46.mid` | ML (N-gram, seed=46) | Chord-conditioned Markov model, temperature=1.0 |

---
## Metrics per file

### before.mid

**Type:** Rule-based (ImproEngine)  
**Description:** Existing lick/arpeggio/scale-walk strategy engine — no ML  

| Metric | Value |
|--------|-------|
| ngram_rep_rate | 0.1795 |
| pitch_range_semitones | 29 |
| large_leap_rate | 0.0500 |
| rhythmic_density | 5.12 |
| in_scale_rate | 0.8537 |
| note_count | 41 |
| rest_count | 0 |

### after_seed_42.mid

**Type:** ML (N-gram, seed=42)  
**Description:** Chord-conditioned Markov model, temperature=1.0  

| Metric | Value |
|--------|-------|
| ngram_rep_rate | 0.0800 |
| pitch_range_semitones | 29 |
| large_leap_rate | 0.0392 |
| rhythmic_density | 6.50 |
| in_scale_rate | 0.9808 |
| note_count | 52 |
| rest_count | 0 |

### after_seed_43.mid

**Type:** ML (N-gram, seed=43)  
**Description:** Chord-conditioned Markov model, temperature=1.0  

| Metric | Value |
|--------|-------|
| ngram_rep_rate | 0.0400 |
| pitch_range_semitones | 26 |
| large_leap_rate | 0.0000 |
| rhythmic_density | 6.50 |
| in_scale_rate | 0.9231 |
| note_count | 52 |
| rest_count | 0 |

### after_seed_44.mid

**Type:** ML (N-gram, seed=44)  
**Description:** Chord-conditioned Markov model, temperature=1.0  

| Metric | Value |
|--------|-------|
| ngram_rep_rate | 0.0000 |
| pitch_range_semitones | 26 |
| large_leap_rate | 0.0000 |
| rhythmic_density | 6.50 |
| in_scale_rate | 0.9423 |
| note_count | 52 |
| rest_count | 0 |

### after_seed_45.mid

**Type:** ML (N-gram, seed=45)  
**Description:** Chord-conditioned Markov model, temperature=1.0  

| Metric | Value |
|--------|-------|
| ngram_rep_rate | 0.0200 |
| pitch_range_semitones | 27 |
| large_leap_rate | 0.0392 |
| rhythmic_density | 6.50 |
| in_scale_rate | 0.9423 |
| note_count | 52 |
| rest_count | 0 |

### after_seed_46.mid

**Type:** ML (N-gram, seed=46)  
**Description:** Chord-conditioned Markov model, temperature=1.0  

| Metric | Value |
|--------|-------|
| ngram_rep_rate | 0.0385 |
| pitch_range_semitones | 27 |
| large_leap_rate | 0.0189 |
| rhythmic_density | 6.75 |
| in_scale_rate | 0.9259 |
| note_count | 54 |
| rest_count | 0 |

---
## Metric Definitions

| Metric | Definition |
|--------|------------|
| `ngram_rep_rate` | Fraction of consecutive pitch 3-grams that repeat (0 = no repetition) |
| `pitch_range_semitones` | Max − min MIDI pitch |
| `large_leap_rate` | Fraction of melodic intervals > 7 semitones |
| `rhythmic_density` | Mean distinct 16th-note onset positions per bar |
| `in_scale_rate` | Fraction of pitches in A natural minor |
| `note_count` | Total pitched notes |
| `rest_count` | Total rests |
