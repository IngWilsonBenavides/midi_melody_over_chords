from __future__ import annotations

from pathlib import Path

import mido

from dictados.domain.phrase import Phrase


class MidiExporter:
    @staticmethod
    def _build_note_track(
        midi: mido.MidiFile,
        phrase: Phrase,
        name: str,
        program: int,
    ) -> None:
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage("track_name", name=name, time=0))
        track.append(mido.Message("program_change", program=program, time=0))

        events = []
        for measure in phrase.measures:
            for note in measure.notes:
                if note.is_audible and note.pitch is not None:
                    events.append(
                        (
                            note.start_tick,
                            1,
                            mido.Message(
                                "note_on",
                                note=note.pitch.midi_number,
                                velocity=note.velocity,
                                time=0,
                            ),
                        )
                    )
                    events.append(
                        (
                            note.end_tick,
                            0,
                            mido.Message(
                                "note_off",
                                note=note.pitch.midi_number,
                                velocity=0,
                                time=0,
                            ),
                        )
                    )

        events.sort(key=lambda item: (item[0], item[1]))
        last_time = 0
        for event_time, _priority, msg in events:
            msg.time = event_time - last_time
            track.append(msg)
            last_time = event_time

        track.append(mido.MetaMessage("end_of_track", time=0))

    @staticmethod
    def _build_metadata_track(
        midi: mido.MidiFile,
        tempo_bpm: int,
        time_signature: tuple[int, int],
        key: str,
    ) -> None:
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
        track.append(
            mido.MetaMessage(
                "time_signature",
                numerator=time_signature[0],
                denominator=time_signature[1],
                time=0,
            )
        )
        track.append(mido.MetaMessage("key_signature", key=key, time=0))
        track.append(mido.MetaMessage("end_of_track", time=0))

    @staticmethod
    def export_phrase(
        phrase: Phrase,
        tempo_bpm: int,
        output_path: Path,
        time_signature: tuple[int, int],
        key: str,
        program: int = 30,
    ) -> None:
        midi = mido.MidiFile(ticks_per_beat=phrase.ppqn)
        MidiExporter._build_metadata_track(midi, tempo_bpm, time_signature, key)
        MidiExporter._build_note_track(midi, phrase, "Dictation", program)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi.save(str(output_path))

    @staticmethod
    def export_two_track(
        melody: Phrase,
        accompaniment: Phrase,
        tempo_bpm: int,
        output_path: Path,
        time_signature: tuple[int, int],
        key: str,
        melody_program: int = 0,
        accompaniment_program: int = 0,
    ) -> None:
        midi = mido.MidiFile(ticks_per_beat=melody.ppqn)
        MidiExporter._build_metadata_track(midi, tempo_bpm, time_signature, key)
        MidiExporter._build_note_track(midi, melody, "Melody", melody_program)
        MidiExporter._build_note_track(midi, accompaniment, "Accompaniment", accompaniment_program)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi.save(str(output_path))
