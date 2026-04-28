"""Melody phrase builder — converts raw (midi, ticks) data into a Phrase.

Takes the output of :class:`~dictados.improviser.engine.ImproEngine` (a list of
per-measure note lists) and wraps it in the domain objects expected by the
existing :class:`~dictados.midi.exporter.MidiExporter`.
"""
from __future__ import annotations

from dictados.domain.chord import Chord
from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.improviser.theory import make_pitch


def build_melody_phrase(
    per_measure_notes: list[list[tuple[int, int]]],
    chords: list[Chord],
    ppqn: int = 480,
    velocity: int = 100,
) -> Phrase:
    """Build a melodic :class:`Phrase` from improviser output.

    Args:
        per_measure_notes: Output of :meth:`ImproEngine.improvise` —
                           one sub-list of ``(midi, ticks)`` per measure.
        chords:            The corresponding chord for each measure.
        ppqn:              Pulses per quarter note.
        velocity:          MIDI velocity for all notes.

    Returns:
        A :class:`Phrase` suitable for :meth:`MidiExporter.export_two_track`.
    """
    measures: list[Measure] = []
    current_tick = 0

    for measure_notes, chord in zip(per_measure_notes, chords):
        notes: list[Note] = []
        measure_ticks = sum(d for _, d in measure_notes)

        for midi, dur in measure_notes:
            notes.append(
                Note(
                    pitch=make_pitch(midi),
                    start_tick=current_tick,
                    duration_ticks=dur,
                    velocity=velocity,
                    note_type="normal",
                )
            )
            current_tick += dur

        measures.append(
            Measure(
                notes=notes,
                chord=chord,
                start_tick=current_tick - measure_ticks,
                duration_ticks=measure_ticks,
            )
        )

    return Phrase(measures=measures, ppqn=ppqn)
