"""Natural-language text parser for chord progressions.

Understands phrases such as:
- ``"4 compases de Am C Dm E"``
- ``"2 ruedas de Am C Dm E"``
- ``"Am C Dm E"``  (implies 1 rueda / 4 compases)
- ``"Am C Dm E, 120bpm"``
- ``"Am C Dm E, swing, 140 bpm"``

Returns a :class:`ParsedProgression` with the chords, number of rounds, tempo,
and an optional style hint.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from dictados.domain.chord import Chord
from dictados.improviser.theory import parse_chord_name

_log = logging.getLogger(__name__)


# ─── Result dataclass ─────────────────────────────────────────────────────────
@dataclass
class ParsedProgression:
    """Parsed result from a free-text chord-progression description."""

    chords: list[Chord]           # Ordered list of chords (one per original measure)
    rounds: int = 1               # Number of times to repeat the progression
    tempo_bpm: int = 120          # Beats per minute
    style: str = "straight"       # "straight", "swing", "latin", etc.
    ppqn: int = 480               # Pulses per quarter note

    @property
    def all_chords(self) -> list[Chord]:
        """Return the full chord sequence repeated *rounds* times."""
        return self.chords * self.rounds


# ─── Chord-name tokeniser ─────────────────────────────────────────────────────
# Match chord tokens like: Am, C, Dm, G7, Cmaj7, F#m, Bb, Ebm7, etc.
_CHORD_RE = re.compile(
    r"\b([A-G][#b]?(?:maj7|m7|dim|aug|sus2|sus4|7|maj|min|m)?)\b"
)
_BPM_RE = re.compile(r"(\d{2,3})\s*bpm", re.IGNORECASE)
_ROUNDS_RE = re.compile(r"(\d+)\s*(?:ruedas?|vueltas?|rounds?)", re.IGNORECASE)
_COMPASES_RE = re.compile(r"(\d+)\s*(?:compases?|bars?|measures?)", re.IGNORECASE)
_STYLE_RE = re.compile(r"\b(swing|latin|bossa|straight|funk|rock|blues)\b", re.IGNORECASE)

# Words to strip before chord detection (Spanish/English filler)
_FILLER = re.compile(
    r"\b(de|en|con|y|a|the|of|in|on|and|over|at|with|genera|crea|make|play)\b",
    re.IGNORECASE,
)


def parse_text(text: str) -> ParsedProgression:
    """Parse a free-text chord progression description.

    Examples
    --------
    >>> parse_text("4 compases de Am C Dm E")
    ParsedProgression(chords=[Am, C, Dm, E], rounds=1, ...)

    >>> parse_text("2 ruedas de Am C Dm E, swing, 130bpm")
    ParsedProgression(chords=[Am, C, Dm, E], rounds=2, tempo_bpm=130, style='swing')
    """
    # ── Tempo ─────────────────────────────────────────────────────────────────
    tempo_bpm = 120
    m = _BPM_RE.search(text)
    if m:
        tempo_bpm = int(m.group(1))

    # ── Style ─────────────────────────────────────────────────────────────────
    style = "straight"
    m = _STYLE_RE.search(text)
    if m:
        style = m.group(1).lower()

    # ── Rounds vs compases ───────────────────────────────────────────────────
    rounds = 1
    m_rounds = _ROUNDS_RE.search(text)
    m_compases = _COMPASES_RE.search(text)

    if m_rounds:
        rounds = int(m_rounds.group(1))
    # If "compases" is given, we treat that number as total measures, not rounds.
    # We'll divide later if the chord count is known.

    # ── Extract chord tokens ──────────────────────────────────────────────────
    # Remove filler words so they don't confuse the chord regex.
    cleaned = _FILLER.sub(" ", text)
    # Also remove numbers (they are beats/bpm/rounds, not notes).
    cleaned = re.sub(r"\b\d+\b", " ", cleaned)
    # Remove punctuation except # and b which are part of chord names.
    cleaned = re.sub(r"[,;:/\\()\[\]]", " ", cleaned)

    tokens = _CHORD_RE.findall(cleaned)
    # Filter obvious false positives (single letters that aren't note names).
    valid_roots = set("CDEFGAB")
    valid_tokens = [t for t in tokens if t[0].upper() in valid_roots]

    if not valid_tokens:
        raise ValueError(
            f"No chord names found in: {text!r}\n"
            "Example: '4 compases de Am C Dm E'"
        )

    chords: list[Chord] = []
    for token in valid_tokens:
        try:
            chords.append(parse_chord_name(token))
        except ValueError as exc:
            _log.warning("Skipping unrecognised chord token %r: %s", token, exc)

    if not chords:
        raise ValueError(f"Could not parse any chords from: {text!r}")

    # If "compases" given and rounds still 1, compute rounds from total/chord_count.
    if m_compases and not m_rounds:
        total_bars = int(m_compases.group(1))
        rounds = max(1, total_bars // len(chords))

    return ParsedProgression(
        chords=chords,
        rounds=rounds,
        tempo_bpm=tempo_bpm,
        style=style,
    )
