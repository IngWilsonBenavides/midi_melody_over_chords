from __future__ import annotations

from pathlib import Path

import yaml

from dictados.config import DictationSpec
from dictados.domain.pitch import Pitch
from dictados.domain.scale import Scale
from dictados.domain.time_signature import TimeSignature
from dictados.generators.phrase_builder import PhraseBuilder
from dictados.generators.progression import ProgressionGenerator, parse_roman_numeral
from dictados.generators.rhythm import RhythmEngine, Subdivision
from dictados.generators.voicing import VoicingEngine
from dictados.midi.exporter import MidiExporter
from dictados.validation.spec_validator import validate_spec


_PC_TO_NAME = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _chord_label(chord) -> str:
    root_name = _PC_TO_NAME[chord.root.pitch_class]
    if chord.quality.value == "minor":
        return f"{root_name}m"
    if chord.quality.value == "diminished":
        return f"{root_name}dim"
    return root_name


def _next_sequence_number(output_dir: Path) -> int:
    max_num = 0
    for path in output_dir.glob("*_melody_chords_*.mid"):
        stem = path.stem
        prefix = stem.split("_melody_chords_", 1)[0]
        if prefix.isdigit():
            max_num = max(max_num, int(prefix))
    return max_num + 1


def _progression_labels(spec, scale: Scale) -> list[str]:
    labels: list[str] = []
    for numeral in spec.progression:
        degree, quality = parse_roman_numeral(numeral)
        chord = scale.chord_from_degree(degree, quality)
        labels.append(_chord_label(chord))
    return labels


def _default_output_path(spec, scale: Scale) -> Path:
    from datetime import datetime

    chord_names = "_".join(_progression_labels(spec, scale))
    timestamp = datetime.now().strftime("%d_%b_%Y_%H_%M").lower()
    output_dir = Path("01_midi_files")
    seq = _next_sequence_number(output_dir)
    filename = f"{seq:02d}_melody_chords_{chord_names}_{timestamp}.mid"
    return output_dir / filename


def generate_dictation(config_path: Path, output_path: Path | None = None) -> Path:
    with config_path.open("r", encoding="ascii") as handle:
        data = yaml.safe_load(handle)

    spec = DictationSpec.model_validate(data)
    errors = validate_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))

    scale = Scale.from_string(spec.key)
    if output_path is None:
        output_path = _default_output_path(spec, scale)

    chords = ProgressionGenerator().expand_progression(spec.progression, spec.groups, scale)

    voicing = VoicingEngine(Pitch.from_midi(spec.range[0]), Pitch.from_midi(spec.range[1]))
    rhythm = RhythmEngine(spec.ppqn)
    builder = PhraseBuilder(voicing, rhythm)

    num, den = (int(x) for x in spec.time_signature.split("/"))
    phrase = builder.build_phrase(
        chords=chords,
        pattern=spec.sequence,
        subdivision=Subdivision.from_string(spec.subdivision),
        time_signature=TimeSignature(num, den),
        ppqn=spec.ppqn,
    )

    MidiExporter.export_phrase(
        phrase=phrase,
        tempo_bpm=spec.tempo,
        output_path=output_path,
        time_signature=(num, den),
        key=spec.key,
        program=spec.program,
    )
    return output_path


if __name__ == "__main__":
    config_file = Path("config.yaml")
    generate_dictation(config_file)
