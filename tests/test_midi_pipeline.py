from pathlib import Path

import mido
import yaml

from dictados.midi.pipeline import process_input_midis


def _write_simple_midi(path: Path) -> None:
    midi = mido.MidiFile(ticks_per_beat=480)
    meta = mido.MidiTrack()
    notes = mido.MidiTrack()
    midi.tracks.append(meta)
    midi.tracks.append(notes)

    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(72), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=3, denominator=4, time=0))
    meta.append(mido.MetaMessage("key_signature", key="D", time=0))
    meta.append(mido.MetaMessage("end_of_track", time=0))

    notes.append(mido.Message("program_change", program=30, time=0))
    notes.append(mido.Message("note_on", note=62, velocity=100, time=0, channel=0))
    notes.append(mido.Message("note_off", note=62, velocity=0, time=480, channel=0))
    notes.append(mido.MetaMessage("end_of_track", time=0))

    midi.save(path)


def test_process_input_midis_generates_outputs(tmp_path: Path):
    input_dir = tmp_path / "01_midi_files" / "input"
    generated_yaml_dir = tmp_path / "01_midi_files" / "generated_files_yaml"
    transposed_midi_dir = tmp_path / "01_midi_files" / "output" / "transposed_c_major"

    input_dir.mkdir(parents=True)
    midi_path = input_dir / "example.mid"
    _write_simple_midi(midi_path)

    outputs = process_input_midis(
        input_dir=input_dir,
        generated_yaml_dir=generated_yaml_dir,
        transposed_midi_dir=transposed_midi_dir,
        program=30,
    )

    assert len(outputs) == 1
    engine_yaml, transposed_yaml, transposed_midi = outputs[0]
    assert engine_yaml.exists()
    assert transposed_yaml.exists()
    assert transposed_midi.exists()

    with engine_yaml.open("r", encoding="utf-8") as handle:
        engine_payload = yaml.safe_load(handle)
    with transposed_yaml.open("r", encoding="utf-8") as handle:
        transposed_payload = yaml.safe_load(handle)

    expected_keys = ["key", "time_signature", "tempo_bpm", "ppqn", "program", "melody"]
    assert list(engine_payload.keys()) == expected_keys
    assert list(transposed_payload.keys()) == expected_keys

    assert "events:" not in engine_yaml.read_text(encoding="utf-8")
    assert "events:" not in transposed_yaml.read_text(encoding="utf-8")
