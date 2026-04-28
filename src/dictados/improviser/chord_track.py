"""Chord track builder.

Builds a MIDI *Phrase* where each measure contains a sustained block chord
(all chord notes played simultaneously for the full measure duration).  This
acts as the harmonic metronome against which the melodic improvisation plays.
"""
from __future__ import annotations

from dictados.domain.chord import Chord
from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.improviser.theory import make_pitch, IMPRO_MIN_MIDI, IMPRO_MAX_MIDI

# MIDI program 0 = Acoustic Grand Piano (used for the chord track)
CHORD_TRACK_PROGRAM = 0

# Velocity for block chords (slightly softer than melody so it stays in background)
CHORD_VELOCITY = 72

# Number of distinct chord voicing notes per block (root + 3rd + 5th for triads)
_TRIAD_INTERVALS = {
    "major":      [0, 4, 7],
    "minor":      [0, 3, 7],
    "diminished": [0, 3, 6],
    "dom7":       [0, 4, 7, 10],
    "maj7":       [0, 4, 7, 11],
    "min7":       [0, 3, 7, 10],
}


def _chord_intervals(chord: Chord) -> list[int]:
    return _TRIAD_INTERVALS.get(chord.quality.value, [0, 4, 7])


def _voicing_midis(chord: Chord, base_midi: int) -> list[int]:
    """Return a close-position voicing starting at or above *base_midi*."""
    root_pc = chord.root.pitch_class
    intervals = _chord_intervals(chord)

    # Find the octave so that root sits just above base_midi.
    root_midi = base_midi
    while root_midi % 12 != root_pc:
        root_midi += 1
    if root_midi > base_midi + 11:
        root_midi -= 12
    root_midi = max(IMPRO_MIN_MIDI, min(root_midi, IMPRO_MAX_MIDI - 12))

    notes = []
    for iv in intervals:
        m = root_midi + iv
        # Keep within sane range.
        while m > IMPRO_MAX_MIDI:
            m -= 12
        notes.append(m)
    return sorted(set(notes))


def build_chord_track(
    chords: list[Chord],
    ppqn: int = 480,
    time_sig_num: int = 4,
) -> Phrase:
    """Build a Phrase where each measure is a block chord.

    Args:
        chords:       One chord per measure.
        ppqn:         Pulses per quarter note.
        time_sig_num: Number of beats per measure.

    Returns:
        A :class:`~dictados.domain.phrase.Phrase` ready for export.
    """
    measure_ticks = time_sig_num * ppqn
    # Start block chords in the lower-middle register (around C4 = MIDI 60).
    base_midi = 48  # C3 — chords sit below the melody

    measures: list[Measure] = []

    for i, chord in enumerate(chords):
        start_tick = i * measure_ticks
        voicing = _voicing_midis(chord, base_midi)

        notes: list[Note] = []
        for midi in voicing:
            notes.append(
                Note(
                    pitch=make_pitch(midi),
                    start_tick=start_tick,
                    duration_ticks=measure_ticks,
                    velocity=CHORD_VELOCITY,
                    note_type="normal",
                )
            )

        measures.append(
            Measure(
                notes=notes,
                chord=chord,
                start_tick=start_tick,
                duration_ticks=measure_ticks,
            )
        )

    return Phrase(measures=measures, ppqn=ppqn)
