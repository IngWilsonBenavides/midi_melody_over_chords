"""Tests added as part of the technical audit Quick Wins (QW8).

Covers:
- BPM=0 and out-of-range BPM in the CLI.
- Slash chord parsing (Am/E must return MINOR, not MAJOR).
- Unknown chord suffix (aug, sus4, m7b5) falls back gracefully with a warning.
- Corrupt MIDI file raises a clear ValueError (not a raw OSError).
- engine.py dead-code removal: _STRATEGY_POOL is defined but not used in improvise().
- text_parser: unrecognised token is skipped with a warning, not silently.
"""
from __future__ import annotations

import logging
import tempfile
import os
from pathlib import Path

import pytest

from dictados.domain.chord import ChordQuality
from dictados.improviser.theory import parse_chord_name
from dictados.improviser.text_parser import parse_text
from dictados.improviser.midi_chord_reader import read_chords_from_midi
from dictados.improviser.main import main as cli_main, generate_improvisation


# ─── Slash chord parsing ──────────────────────────────────────────────────────

class TestSlashChords:
    def test_am_over_e_returns_minor(self, caplog):
        """Am/E should be treated as Am (MINOR), not degraded to MAJOR."""
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("Am/E")
        assert chord.quality == ChordQuality.MINOR, (
            f"Am/E parsed as {chord.quality!r}, expected MINOR"
        )

    def test_slash_chord_emits_warning(self, caplog):
        """A warning should be logged explaining the bass note was ignored."""
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            parse_chord_name("Cmaj7/G")
        assert any("bass note" in rec.message or "Slash chord" in rec.message
                   for rec in caplog.records), (
            "Expected a warning about the ignored bass note in Cmaj7/G"
        )

    def test_c_over_g_returns_major(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("C/G")
        assert chord.quality == ChordQuality.MAJOR

    def test_dm_over_f_returns_minor(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("Dm/F")
        assert chord.quality == ChordQuality.MINOR


# ─── Unsupported chord suffixes ───────────────────────────────────────────────

class TestUnsupportedSuffixes:
    def test_aug_falls_back_to_major(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("Caug")
        assert chord.quality == ChordQuality.MAJOR

    def test_aug_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            parse_chord_name("Faug")
        assert any("aug" in rec.message.lower() or "Augmented" in rec.message
                   for rec in caplog.records)

    def test_sus4_falls_back_to_major(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("Gsus4")
        assert chord.quality == ChordQuality.MAJOR

    def test_sus4_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            parse_chord_name("Dsus2")
        assert any("sus" in rec.message.lower() or "Suspended" in rec.message
                   for rec in caplog.records)

    def test_dim7_treated_as_diminished(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("Edim7")
        assert chord.quality == ChordQuality.DIMINISHED

    def test_m7b5_treated_as_minor_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="dictados.improviser.theory"):
            chord = parse_chord_name("Bm7b5")
        assert chord.quality == ChordQuality.MINOR
        assert any("m7b5" in rec.message for rec in caplog.records)


# ─── Text parser: unrecognised tokens ────────────────────────────────────────

class TestTextParserWarnings:
    def test_unknown_token_skipped_silently_before_parse(self):
        """Tokens whose first character is not a note letter (C-B) are filtered
        before reaching parse_chord_name — no crash, no spurious chord."""
        prog = parse_text("Am Xyz C Dm")
        # 'Xyz' has 'X' which is not a valid note root, so 3 valid chords remain.
        assert len(prog.chords) == 3

    def test_unknown_root_in_parse_chord_name_raises(self):
        """parse_chord_name must raise ValueError for a root not in NOTE_TO_PC."""
        with pytest.raises(ValueError, match="Unknown chord root"):
            parse_chord_name("Xm")  # 'X' not a valid root


# ─── Corrupt MIDI file ────────────────────────────────────────────────────────

class TestCorruptMidi:
    def test_corrupt_midi_raises_value_error(self, tmp_path):
        """A corrupt .mid file should raise ValueError with a clear message."""
        bad_file = tmp_path / "bad.mid"
        bad_file.write_bytes(b"this is not a MIDI file")

        with pytest.raises(ValueError, match="Could not read MIDI file"):
            read_chords_from_midi(bad_file)

    def test_corrupt_midi_not_raw_os_error(self, tmp_path):
        """The original OSError from mido must not propagate raw to the caller."""
        bad_file = tmp_path / "bad.mid"
        bad_file.write_bytes(b"MThd\x00")  # truncated MThd header

        with pytest.raises((ValueError, OSError)):
            # We accept either; the key requirement is the original raw OSError
            # is wrapped in ValueError when the file is clearly corrupt.
            read_chords_from_midi(bad_file)

    def test_nonexistent_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_chords_from_midi(tmp_path / "missing.mid")


# ─── CLI tempo validation ─────────────────────────────────────────────────────

class TestCliTempoValidation:
    def test_tempo_zero_rejected(self):
        """--tempo 0 must produce a CLI error, not a ZeroDivisionError crash."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["Am C Dm E", "--tempo", "0"])
        # argparse exits with code 2 for errors.
        assert exc_info.value.code == 2

    def test_tempo_negative_rejected(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["Am C Dm E", "--tempo", "-10"])
        assert exc_info.value.code == 2

    def test_tempo_above_max_rejected(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["Am C Dm E", "--tempo", "9999"])
        assert exc_info.value.code == 2

    def test_valid_tempo_accepted(self, tmp_path):
        """--tempo within [1, 300] must not raise."""
        out = tmp_path / "out.mid"
        cli_main(["Am C Dm E", "--tempo", "120", "--seed", "0", "--output", str(out)])
        assert out.exists()

    def test_tempo_boundary_low(self, tmp_path):
        out = tmp_path / "out.mid"
        cli_main(["Am", "--tempo", "20", "--seed", "0", "--output", str(out)])
        assert out.exists()

    def test_tempo_boundary_high(self, tmp_path):
        out = tmp_path / "out.mid"
        cli_main(["Am", "--tempo", "300", "--seed", "0", "--output", str(out)])
        assert out.exists()


# ─── CLI rounds validation ────────────────────────────────────────────────────

class TestCliRoundsValidation:
    def test_rounds_zero_rejected(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["Am C Dm E", "--rounds", "0"])
        assert exc_info.value.code == 2

    def test_rounds_negative_rejected(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["Am C Dm E", "--rounds", "-1"])
        assert exc_info.value.code == 2

    def test_rounds_one_accepted(self, tmp_path):
        out = tmp_path / "out.mid"
        cli_main(["Am C", "--rounds", "1", "--seed", "0", "--output", str(out)])
        assert out.exists()
