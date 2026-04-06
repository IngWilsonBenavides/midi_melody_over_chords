from pathlib import Path

import mido
import yaml

from dictados.midi.importer import MidiImporter


def _build_sample_midi(path: Path, key: str = "G") -> None:
    midi = mido.MidiFile(ticks_per_beat=480)
    meta = mido.MidiTrack()
    notes = mido.MidiTrack()
    midi.tracks.append(meta)
    midi.tracks.append(notes)

    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(60), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("key_signature", key=key, time=0))
    meta.append(mido.MetaMessage("end_of_track", time=0))

    notes.append(mido.Message("program_change", program=30, time=0))
    notes.append(mido.Message("note_on", note=67, velocity=100, time=0, channel=0))
    notes.append(mido.Message("note_off", note=67, velocity=0, time=480, channel=0))
    notes.append(mido.Message("note_on", note=69, velocity=100, time=0, channel=0))
    notes.append(mido.Message("note_off", note=69, velocity=0, time=480, channel=0))
    notes.append(mido.MetaMessage("end_of_track", time=0))

    midi.save(path)


def test_midi_importer_imports_phrase_and_metadata(tmp_path: Path):
    midi_path = tmp_path / "sample.mid"
    _build_sample_midi(midi_path, key="G")

    importer = MidiImporter()
    imported = importer.import_midi(midi_path)

    assert imported.metadata.ppqn == 480
    assert imported.metadata.tempo_bpm == 60
    assert imported.metadata.time_signature == "4/4"
    assert imported.metadata.key_signature == "G"
    assert imported.metadata.note_count == 2
    assert imported.events[0].pitch == 67
    assert imported.phrase.measures


def test_transpose_to_c_major_from_g_major(tmp_path: Path):
    midi_path = tmp_path / "sample.mid"
    _build_sample_midi(midi_path, key="G")

    importer = MidiImporter()
    imported = importer.import_midi(midi_path)
    transposed = importer.transpose_to_c_major(imported.phrase, imported.metadata.key_signature)

    transposed_notes = [
        note.pitch.midi_number
        for measure in transposed.measures
        for note in measure.notes
        if note.pitch is not None and note.note_type == "normal"
    ]
    assert transposed_notes[:2] == [60, 62]


def test_generate_from_input_creates_three_outputs(tmp_path: Path):
    input_midi = tmp_path / "source.mid"
    _build_sample_midi(input_midi, key="G")

    generated_yaml = tmp_path / "generated_files_yaml"
    transposed_midis = tmp_path / "transposed_c_major"

    importer = MidiImporter()
    engine_yaml, transposed_yaml, transposed_midi = importer.generate_from_input(
        midi_path=input_midi,
        generated_yaml_dir=generated_yaml,
        transposed_midi_dir=transposed_midis,
        program=30,
    )

    assert engine_yaml.exists()
    assert transposed_yaml.exists()
    assert transposed_midi.exists()

    with engine_yaml.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    assert list(payload.keys()) == ["key", "time_signature", "tempo_bpm", "ppqn", "program", "melody"]
    assert payload["ppqn"] == 480
    assert payload["program"] == 30

    content = engine_yaml.read_text(encoding="utf-8")
    assert "notes: [" in content
    assert "rhythm: [" in content
    assert "events:" not in content
