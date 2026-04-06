from __future__ import annotations

from pathlib import Path

from dictados.midi.importer import MidiImporter


def process_input_midis(
    input_dir: Path = Path("01_midi_files") / "input",
    generated_yaml_dir: Path = Path("01_midi_files") / "generated_files_yaml",
    transposed_midi_dir: Path = Path("01_midi_files") / "output" / "transposed_c_major",
    program: int = 30,
) -> list[tuple[Path, Path, Path]]:
    importer = MidiImporter()
    outputs: list[tuple[Path, Path, Path]] = []

    for midi_path in sorted(input_dir.glob("*.mid")):
        outputs.append(
            importer.generate_from_input(
                midi_path=midi_path,
                generated_yaml_dir=generated_yaml_dir,
                transposed_midi_dir=transposed_midi_dir,
                program=program,
            )
        )

    return outputs
