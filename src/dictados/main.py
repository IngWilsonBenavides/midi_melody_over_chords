from __future__ import annotations

from pathlib import Path
from datetime import datetime

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
    for path in output_dir.glob("*.mid"):
        stem = path.stem
        # Try to extract number from beginning of filename
        parts = stem.split("_")
        if parts[0].isdigit():
            max_num = max(max_num, int(parts[0]))
    return max_num + 1


def _progression_labels(spec, scale: Scale) -> list[str]:
    labels: list[str] = []
    for numeral in spec.progression:
        degree, quality = parse_roman_numeral(numeral)
        chord = scale.chord_from_degree(degree, quality)
        labels.append(_chord_label(chord))
    return labels


def _default_output_path_generated(spec, scale: Scale) -> Path:
    """Generate output path for generated melody mode."""
    chord_names = "_".join(_progression_labels(spec, scale))
    timestamp = datetime.now().strftime("%d_%b_%Y_%H_%M").lower()
    output_dir = Path("01_midi_files") / "output"
    seq = _next_sequence_number(output_dir)
    filename = f"{seq:02d}_melody_chords_{chord_names}_{timestamp}.mid"
    return output_dir / filename


def _default_output_path_melody(spec) -> Path:
    """Generate output path for specific melody mode."""
    timestamp = datetime.now().strftime("%d_%b_%Y_%H_%M").lower()
    output_dir = Path("01_midi_files") / "output"
    seq = _next_sequence_number(output_dir)
    filename = f"{seq:02d}_melody_{spec.key}_{timestamp}.mid"
    return output_dir / filename


def generate_dictation(config_path: Path, output_path: Path | None = None) -> Path:
    """Generate dictation from config file.
    
    Supports two modes:
    1. Generated: progression + groups (original behavior)
    2. Specific melody: melody with explicit notes and rhythms
    """
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    spec = DictationSpec.model_validate(data)
    errors = validate_spec(spec) if spec.melody is None else []
    if errors:
        raise ValueError("; ".join(errors))

    num, den = map(int, spec.time_signature.split("/"))
    time_signature = TimeSignature(num, den)
    rhythm_engine = RhythmEngine(spec.ppqn)
    
    # MODE 1: Specific Melody
    if spec.melody is not None:
        if output_path is None:
            output_path = _default_output_path_melody(spec)
        
        builder = PhraseBuilder(None, rhythm_engine)
        phrase = builder.build_phrase_from_melody(
            melody_measures=spec.melody,
            ppqn=spec.ppqn,
        )
    # MODE 2: Generated Melody
    else:
        scale = Scale.from_string(spec.key)
        if output_path is None:
            output_path = _default_output_path_generated(spec, scale)
        
        chords = ProgressionGenerator().expand_progression(spec.progression, spec.groups, scale)
        voicing = VoicingEngine(Pitch.from_midi(spec.range[0]), Pitch.from_midi(spec.range[1]))
        builder = PhraseBuilder(voicing, rhythm_engine)
        
        phrase = builder.build_phrase(
            chords=chords,
            pattern=spec.sequence,
            subdivision=Subdivision.from_string(spec.subdivision),
            time_signature=time_signature,
            ppqn=spec.ppqn,
        )

    # Export MIDI
    tempo_bpm = spec.tempo_bpm if spec.tempo_bpm else spec.tempo
    MidiExporter.export_phrase(
        phrase=phrase,
        tempo_bpm=tempo_bpm,
        output_path=output_path,
        time_signature=(num, den),
        key=spec.key,
        program=spec.program,
    )
    return output_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        config_file = Path(sys.argv[1])
    else:
        config_file = Path("config.yaml")
    
    output = generate_dictation(config_file)
    print(f"✅ Generated: {output}")

