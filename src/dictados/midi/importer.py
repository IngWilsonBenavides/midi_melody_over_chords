from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mido
import yaml

from dictados.domain.note import Note
from dictados.domain.phrase import Measure, Phrase
from dictados.domain.pitch import MAX_MIDI, MIN_MIDI, Pitch
from dictados.generators.rhythm_parser import NOTATION_TO_BEATS


PC_TO_NAME = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KEY_TO_PC = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}


class _FlowList(list):
    pass


class _MinimalYamlDumper(yaml.SafeDumper):
    pass


def _represent_flow_list(dumper: yaml.SafeDumper, data: _FlowList):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


_MinimalYamlDumper.add_representer(_FlowList, _represent_flow_list)


def _midi_to_note_name(midi_number: int) -> str:
    return PC_TO_NAME[midi_number % 12]


def _ticks_to_rhythm_symbol(ticks: int, ppqn: int) -> str:
    for notation, beats in NOTATION_TO_BEATS.items():
        if int(beats * ppqn) == ticks:
            return notation
    return f"ticks_{ticks}"


def _fit_to_engine_range(midi_number: int) -> int:
    value = midi_number
    while value < MIN_MIDI:
        value += 12
    while value > MAX_MIDI:
        value -= 12
    if value < MIN_MIDI:
        return MIN_MIDI
    if value > MAX_MIDI:
        return MAX_MIDI
    return value


@dataclass(frozen=True)
class MidiNoteEvent:
    pitch: int
    start_tick: int
    duration_ticks: int
    velocity: int
    channel: int
    track: int


@dataclass(frozen=True)
class MidiMetadata:
    tempo_bpm: int
    ppqn: int
    time_signature: str
    key_signature: str | None
    tracks: int
    channels: list[int]
    total_ticks: int
    total_duration_seconds: float
    melodic_range_min: int | None
    melodic_range_max: int | None
    note_count: int
    rest_count: int


@dataclass(frozen=True)
class ImportedMidi:
    phrase: Phrase
    metadata: MidiMetadata
    events: list[MidiNoteEvent]


class MidiImporter:
    def import_midi(self, midi_path: Path) -> ImportedMidi:
        midi = mido.MidiFile(str(midi_path))

        tempo = 500000
        numerator = 4
        denominator = 4
        key_signature: str | None = None
        total_ticks = 0
        raw_events: list[MidiNoteEvent] = []

        for track_index, track in enumerate(midi.tracks):
            abs_time = 0
            active_notes: dict[tuple[int, int], tuple[int, int]] = {}
            for msg in track:
                abs_time += msg.time
                if msg.is_meta:
                    if msg.type == "set_tempo":
                        tempo = msg.tempo
                    elif msg.type == "time_signature":
                        numerator = msg.numerator
                        denominator = msg.denominator
                    elif msg.type == "key_signature":
                        key_signature = msg.key
                    continue

                if msg.type == "note_on" and msg.velocity > 0:
                    active_notes[(msg.channel, msg.note)] = (abs_time, msg.velocity)
                elif msg.type in {"note_off", "note_on"}:
                    key = (msg.channel, msg.note)
                    if key in active_notes:
                        start_tick, velocity = active_notes.pop(key)
                        duration = max(1, abs_time - start_tick)
                        raw_events.append(
                            MidiNoteEvent(
                                pitch=msg.note,
                                start_tick=start_tick,
                                duration_ticks=duration,
                                velocity=velocity,
                                channel=msg.channel,
                                track=track_index,
                            )
                        )
                total_ticks = max(total_ticks, abs_time)

        events = sorted(raw_events, key=lambda event: (event.start_tick, event.pitch, event.channel))
        phrase, rest_count = self._events_to_phrase(events, midi.ticks_per_beat, numerator, denominator)

        channels = sorted({event.channel for event in events})
        melodic_min = min((event.pitch for event in events), default=None)
        melodic_max = max((event.pitch for event in events), default=None)
        tempo_bpm = int(round(mido.tempo2bpm(tempo)))
        total_seconds = float(mido.tick2second(total_ticks, midi.ticks_per_beat, tempo))

        metadata = MidiMetadata(
            tempo_bpm=tempo_bpm,
            ppqn=midi.ticks_per_beat,
            time_signature=f"{numerator}/{denominator}",
            key_signature=key_signature,
            tracks=len(midi.tracks),
            channels=channels,
            total_ticks=total_ticks,
            total_duration_seconds=round(total_seconds, 3),
            melodic_range_min=melodic_min,
            melodic_range_max=melodic_max,
            note_count=len(events),
            rest_count=rest_count,
        )
        return ImportedMidi(phrase=phrase, metadata=metadata, events=events)

    def transpose_to_c_major(self, phrase: Phrase, detected_key: str | None) -> Phrase:
        tonic_pc = self._resolve_tonic_pitch_class(phrase, detected_key)
        shift = -tonic_pc

        transposed_measures: list[Measure] = []
        for measure in phrase.measures:
            transposed_notes: list[Note] = []
            for note in measure.notes:
                if note.note_type != "normal" or note.pitch is None:
                    transposed_notes.append(note)
                    continue
                transposed_midi = _fit_to_engine_range(note.pitch.midi_number + shift)
                transposed_notes.append(
                    Note(
                        pitch=Pitch.from_midi(transposed_midi),
                        start_tick=note.start_tick,
                        duration_ticks=note.duration_ticks,
                        velocity=note.velocity,
                        note_type=note.note_type,
                    )
                )
            transposed_measures.append(
                Measure(
                    notes=transposed_notes,
                    chord=measure.chord,
                    start_tick=measure.start_tick,
                    duration_ticks=measure.duration_ticks,
                )
            )

        return Phrase(measures=transposed_measures, ppqn=phrase.ppqn)

    def export_phrase_to_yaml(
        self,
        phrase: Phrase,
        metadata: MidiMetadata,
        output_path: Path,
        program: int,
    ) -> None:
        melody: list[dict] = []
        for index, measure in enumerate(phrase.measures, start=1):
            notes = []
            rhythms = []
            for note in measure.notes:
                if note.note_type == "normal" and note.pitch is not None:
                    notes.append(_midi_to_note_name(note.pitch.midi_number))
                elif note.note_type == "rest":
                    notes.append("-")
                elif note.note_type == "ghost":
                    notes.append("~")
                else:
                    notes.append("x")
                rhythms.append(_ticks_to_rhythm_symbol(note.duration_ticks, phrase.ppqn))

            melody.append(
                {
                    "compas": index,
                    "notes": _FlowList(notes),
                    "rhythm": _FlowList(rhythms),
                }
            )

        payload: dict = {
            "key": metadata.key_signature or "unknown",
            "time_signature": metadata.time_signature,
            "tempo_bpm": metadata.tempo_bpm,
            "ppqn": metadata.ppqn,
            "program": program,
            "melody": melody,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.dump(payload, handle, Dumper=_MinimalYamlDumper, allow_unicode=True, sort_keys=False)

    def generate_from_input(
        self,
        midi_path: Path,
        generated_yaml_dir: Path,
        transposed_midi_dir: Path,
        program: int = 30,
    ) -> tuple[Path, Path, Path]:
        imported = self.import_midi(midi_path)
        base_name = midi_path.stem

        original_yaml_path = generated_yaml_dir / f"{base_name}_engine.yaml"
        self.export_phrase_to_yaml(
            phrase=imported.phrase,
            metadata=imported.metadata,
            output_path=original_yaml_path,
            program=program,
        )

        transposed_phrase = self.transpose_to_c_major(imported.phrase, imported.metadata.key_signature)
        transposed_yaml_path = generated_yaml_dir / f"{base_name}_to_C_major.yaml"
        transposed_metadata = MidiMetadata(
            tempo_bpm=imported.metadata.tempo_bpm,
            ppqn=imported.metadata.ppqn,
            time_signature=imported.metadata.time_signature,
            key_signature="C",
            tracks=imported.metadata.tracks,
            channels=imported.metadata.channels,
            total_ticks=imported.metadata.total_ticks,
            total_duration_seconds=imported.metadata.total_duration_seconds,
            melodic_range_min=min(
                (note.pitch.midi_number for measure in transposed_phrase.measures for note in measure.notes if note.pitch is not None),
                default=None,
            ),
            melodic_range_max=max(
                (note.pitch.midi_number for measure in transposed_phrase.measures for note in measure.notes if note.pitch is not None),
                default=None,
            ),
            note_count=imported.metadata.note_count,
            rest_count=imported.metadata.rest_count,
        )
        self.export_phrase_to_yaml(
            phrase=transposed_phrase,
            metadata=transposed_metadata,
            output_path=transposed_yaml_path,
            program=program,
        )

        from dictados.midi.exporter import MidiExporter

        transposed_midi_path = transposed_midi_dir / f"{base_name}_to_C_major.mid"
        num, den = map(int, imported.metadata.time_signature.split("/"))
        MidiExporter.export_phrase(
            phrase=transposed_phrase,
            tempo_bpm=imported.metadata.tempo_bpm,
            output_path=transposed_midi_path,
            time_signature=(num, den),
            key="C",
            program=program,
        )
        return original_yaml_path, transposed_yaml_path, transposed_midi_path

    def _resolve_tonic_pitch_class(self, phrase: Phrase, detected_key: str | None) -> int:
        if detected_key:
            cleaned = detected_key.replace("m", "").replace("M", "").strip().upper()
            if cleaned in KEY_TO_PC:
                return KEY_TO_PC[cleaned]
        return self._estimate_tonic_pitch_class(phrase)

    def _estimate_tonic_pitch_class(self, phrase: Phrase) -> int:
        histogram = [0] * 12
        for measure in phrase.measures:
            for note in measure.notes:
                if note.note_type == "normal" and note.pitch is not None:
                    histogram[note.pitch.pitch_class] += note.duration_ticks
        max_weight = max(histogram)
        if max_weight == 0:
            return 0
        return histogram.index(max_weight)

    def _events_to_phrase(
        self,
        events: list[MidiNoteEvent],
        ppqn: int,
        numerator: int,
        denominator: int,
    ) -> tuple[Phrase, int]:
        measure_ticks = int(numerator * ppqn * (4 / denominator))
        if measure_ticks <= 0:
            measure_ticks = 4 * ppqn

        if not events:
            return Phrase(measures=[], ppqn=ppqn), 0

        filtered = [event for event in events if MIN_MIDI <= event.pitch <= MAX_MIDI]
        if not filtered:
            return Phrase(measures=[], ppqn=ppqn), 0

        last_end = max(event.start_tick + event.duration_ticks for event in filtered)
        measure_count = max(1, (last_end + measure_ticks - 1) // measure_ticks)

        measures: list[Measure] = []
        rest_count = 0
        sorted_events = sorted(filtered, key=lambda event: (event.start_tick, event.pitch))
        cursor = 0

        for measure_index in range(measure_count):
            measure_start = measure_index * measure_ticks
            measure_end = measure_start + measure_ticks

            measure_events = [
                event
                for event in sorted_events
                if measure_start <= event.start_tick < measure_end
            ]
            notes: list[Note] = []

            local_cursor = measure_start
            for event in measure_events:
                if event.start_tick > local_cursor:
                    rest_count += 1
                    notes.append(
                        Note(
                            pitch=None,
                            start_tick=local_cursor,
                            duration_ticks=event.start_tick - local_cursor,
                            velocity=0,
                            note_type="rest",
                        )
                    )
                note = Note(
                    pitch=Pitch.from_midi(_fit_to_engine_range(event.pitch)),
                    start_tick=event.start_tick,
                    duration_ticks=event.duration_ticks,
                    velocity=event.velocity,
                    note_type="normal",
                )
                notes.append(note)
                local_cursor = max(local_cursor, event.start_tick + event.duration_ticks)

            if local_cursor < measure_end:
                rest_count += 1
                notes.append(
                    Note(
                        pitch=None,
                        start_tick=local_cursor,
                        duration_ticks=measure_end - local_cursor,
                        velocity=0,
                        note_type="rest",
                    )
                )

            measures.append(
                Measure(
                    notes=notes,
                    chord=None,
                    start_tick=measure_start,
                    duration_ticks=measure_ticks,
                )
            )
            cursor = measure_end

        _ = cursor
        return Phrase(measures=measures, ppqn=ppqn), rest_count
