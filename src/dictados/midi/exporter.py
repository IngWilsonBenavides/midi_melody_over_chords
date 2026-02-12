from __future__ import annotations

from pathlib import Path

import mido

from dictados.domain.phrase import Phrase


class MidiExporter:
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
        track0 = mido.MidiTrack()
        track1 = mido.MidiTrack()
        midi.tracks.append(track0)
        midi.tracks.append(track1)

        track0.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
        track0.append(
            mido.MetaMessage(
                "time_signature",
                numerator=time_signature[0],
                denominator=time_signature[1],
                time=0,
            )
        )
        track0.append(mido.MetaMessage("key_signature", key=key, time=0))
        track0.append(mido.MetaMessage("end_of_track", time=0))

        track1.append(mido.MetaMessage("track_name", name="Dictation", time=0))
        track1.append(mido.Message("program_change", program=program, time=0))

        events = []
        for measure in phrase.measures:
            for note in measure.notes:
                events.append((note.start_tick, 1, mido.Message("note_on", note=note.pitch.midi_number, velocity=note.velocity, time=0)))
                events.append((note.end_tick, 0, mido.Message("note_off", note=note.pitch.midi_number, velocity=0, time=0)))

        events.sort(key=lambda item: (item[0], item[1]))
        last_time = 0
        for event_time, _priority, msg in events:
            msg.time = event_time - last_time
            track1.append(msg)
            last_time = event_time

        track1.append(mido.MetaMessage("end_of_track", time=0))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        midi.save(str(output_path))
