# Dataset Sources and Licensing

This directory holds the data used to train the melodic improviser.

```
data/
├── raw/          ← original MIDI files (not committed to git — download separately)
├── processed/    ← JSONLines produced by tools/dataset/build_dataset.py
└── splits/       ← train.jsonl / val.jsonl / test.jsonl
```

---

## Approved sources

All sources below are licensed for research and derivative works.
Processed examples inherit their source license.

### 1. Lakh MIDI Dataset (LMD)
- **URL**: <https://colinraffel.com/projects/lmd/>
- **License**: CC BY 4.0
- **Content**: ~176 k multi-genre MIDI files
- **Download**:
  ```bash
  bash scripts/download_sources.sh lakh
  ```
- **How used**: Monophonic melody track extracted per file; chord context
  inferred from accompanying tracks where present.

### 2. NES Music Database (NESMDB)
- **URL**: <https://github.com/chrisdonahue/nesmdb>
- **License**: CC BY 4.0 (processed MIDI export)
- **Content**: ~5 k chiptune tracks — melody tracks are inherently monophonic
- **Download**:
  ```bash
  bash scripts/download_sources.sh nesmdb
  ```

### 3. MusicNet
- **URL**: <https://zenodo.org/record/5120004>
- **License**: CC BY 4.0
- **Content**: Classical music with detailed annotations (MIDI + audio)
- **Download**:
  ```bash
  bash scripts/download_sources.sh musicnet
  ```

### 4. Built-in licks (phrase_library.py)
- **License**: Project-owned (MIT, same as repo)
- **Content**: 20 hand-crafted licks in the improviser — exported to MIDI and
  re-ingested as seed training examples.

---

## Placing your own MIDI files

Drop any legally-sourced `.mid` files into `data/raw/<style>/` subdirectories,
e.g.:

```
data/raw/jazz/myCoolHead.mid
data/raw/blues/shuffleBlues.mid
data/raw/rock/pentatonicSolo.mid
```

The `style` subdirectory name is used as the style tag in metadata when no
other style information is available.

---

## Reproduction instructions

```bash
# 1. Download approved sources
bash scripts/download_sources.sh all

# 2. Build the full dataset
bash scripts/build_dataset.sh

# 3. View statistics report
open reports/dataset_summary.md
```

---

## What is NOT committed

- `data/raw/**/*.mid` — original MIDI files (excluded via `.gitignore`)
- `data/processed/*.jsonl` — generated artefacts; reproduce via build script
- `data/splits/*.jsonl` — generated artefacts; reproduce via build script

---

## License summary

| Source | License | Attribution required |
|--------|---------|---------------------|
| Lakh MIDI Dataset | CC BY 4.0 | Yes — cite Colin Raffel (2016) |
| NESMDB | CC BY 4.0 | Yes — cite Donahue et al. (2018) |
| MusicNet | CC BY 4.0 | Yes — cite Thickstun et al. (2017) |
| Built-in licks | MIT | No |
