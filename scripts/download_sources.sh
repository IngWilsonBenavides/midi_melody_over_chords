#!/usr/bin/env bash
# download_sources.sh — download approved open-license MIDI sources.
#
# Usage:
#   bash scripts/download_sources.sh all       # download all sources
#   bash scripts/download_sources.sh lakh      # Lakh MIDI Dataset only
#   bash scripts/download_sources.sh nesmdb    # NES Music Database only
#   bash scripts/download_sources.sh musicnet  # MusicNet only
#
# Prerequisites: wget or curl, unzip/tar.
#
# Files are downloaded into data/raw/<source>/.
# Large archives are extracted in-place; the compressed files are removed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw"
mkdir -p "$RAW_DIR"

# ─── Helper ──────────────────────────────────────────────────────────────────

download() {
    local url="$1"
    local dest="$2"
    if command -v wget &>/dev/null; then
        wget -q --show-progress -O "$dest" "$url"
    elif command -v curl &>/dev/null; then
        curl -L --progress-bar -o "$dest" "$url"
    else
        echo "ERROR: neither wget nor curl found." >&2
        exit 1
    fi
}

# ─── Lakh MIDI Dataset (LMD-matched) ─────────────────────────────────────────
# License: CC BY 4.0
# Citation: Raffel, C. (2016). "Learning-Based Methods for Comparing Sequences,
#           with Applications to Audio-to-MIDI Alignment and Matching."
#           PhD Thesis, Columbia University.

download_lakh() {
    local dest_dir="$RAW_DIR/lakh"
    mkdir -p "$dest_dir"
    echo "Downloading Lakh MIDI Dataset (LMD-matched, ~1.5 GB) …"
    local url="http://hog.ee.columbia.edu/craffel/lmd/lmd_matched.tar.gz"
    local archive="$dest_dir/lmd_matched.tar.gz"
    download "$url" "$archive"
    echo "Extracting …"
    tar -xzf "$archive" -C "$dest_dir" --strip-components=1
    rm "$archive"
    echo "Lakh MIDI Dataset downloaded to $dest_dir"
}

# ─── NES Music Database ───────────────────────────────────────────────────────
# License: CC BY 4.0
# Citation: Donahue, C. et al. (2018). "The NES Music Database: A Multi-Instrumental
#           Dataset with Expressive Performance Attributes." ISMIR 2018.

download_nesmdb() {
    local dest_dir="$RAW_DIR/nesmdb"
    mkdir -p "$dest_dir"
    echo "Downloading NES Music Database MIDI export (~50 MB) …"
    local url="https://github.com/chrisdonahue/nesmdb/releases/download/v1.0/nesmdb_midi.tar.gz"
    local archive="$dest_dir/nesmdb_midi.tar.gz"
    download "$url" "$archive"
    echo "Extracting …"
    tar -xzf "$archive" -C "$dest_dir" --strip-components=1
    rm "$archive"
    echo "NESMDB downloaded to $dest_dir"
}

# ─── MusicNet ─────────────────────────────────────────────────────────────────
# License: CC BY 4.0
# Citation: Thickstun, J. et al. (2017). "Learning Features of Music from Scratch."
#           ICLR 2017.

download_musicnet() {
    local dest_dir="$RAW_DIR/musicnet"
    mkdir -p "$dest_dir"
    echo "Downloading MusicNet MIDI files (~10 MB) …"
    local url="https://zenodo.org/record/5120004/files/musicnet_midis.tar.gz"
    local archive="$dest_dir/musicnet_midis.tar.gz"
    download "$url" "$archive"
    echo "Extracting …"
    tar -xzf "$archive" -C "$dest_dir" --strip-components=1
    rm "$archive"
    echo "MusicNet downloaded to $dest_dir"
}

# ─── Dispatch ─────────────────────────────────────────────────────────────────

SOURCE="${1:-all}"

case "$SOURCE" in
    lakh)
        download_lakh
        ;;
    nesmdb)
        download_nesmdb
        ;;
    musicnet)
        download_musicnet
        ;;
    all)
        download_lakh
        download_nesmdb
        download_musicnet
        ;;
    *)
        echo "Unknown source: $SOURCE"
        echo "Usage: bash scripts/download_sources.sh [all|lakh|nesmdb|musicnet]"
        exit 1
        ;;
esac

echo ""
echo "Download complete. Run 'bash scripts/build_dataset.sh' to build the dataset."
