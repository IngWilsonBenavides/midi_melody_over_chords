.PHONY: dataset train demo test clean

PYTHON   ?= python
CONFIG   ?= configs/ml_config.yaml
PPQN     ?= 480
TEMPO    ?= 100
SEED     ?= 42
TEMP     ?= 1.0

# ── Build (or rebuild) the training dataset ───────────────────────────────────
dataset:
	$(PYTHON) scripts/generate_seed_midis.py
	$(PYTHON) -m tools.dataset.build_dataset \
		--input-dir data/raw \
		--output-dir data \
		--report

# ── Train the chord-conditioned n-gram model ─────────────────────────────────
train:
	$(PYTHON) -m ml.train --config $(CONFIG)

# ── Re-train from scratch (regenerates dataset first) ────────────────────────
train-fresh:
	$(PYTHON) -m ml.train --config $(CONFIG) --regenerate-dataset

# ── Generate demo MIDIs and evaluation report ─────────────────────────────────
demo:
	$(PYTHON) -m ml.export_demo --config $(CONFIG)

# ── Generate a single ML melody (quick test) ─────────────────────────────────
infer:
	$(PYTHON) -m ml.infer --config $(CONFIG) \
		--seed $(SEED) --temperature $(TEMP) \
		--out outputs/ml_melody.mid

# ── Run all tests ─────────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v

# ── Clean generated artifacts (keep source) ───────────────────────────────────
clean:
	rm -rf outputs/*.mid models/*.pkl reports/demo_summary.md

# ── Full pipeline: dataset → train → demo → test ──────────────────────────────
all: dataset train demo test
