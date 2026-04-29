"""
Note name parser.
Converts musical note names (C, D, E, etc.) to MIDI numbers.
"""

from __future__ import annotations

from dictados.domain.pitch import Pitch


# Chromatic scale: C=0, C#=1, D=2, etc.
NOTE_NAME_TO_PC = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

SEMITONE_MODIFIERS = {
    "#": 1,      # sharp
    "♯": 1,      # sharp (unicode)
    "b": -1,     # flat
    "♭": -1,     # flat (unicode)
}

# Special symbols
SYMBOLS = {
    "-": "rest",        # rest
    "rest": "rest",
    "~": "ghost",       # ghost note
    "ghost": "ghost",
    "x": "muted",       # muted note
}


def parse_note_name(name: str, default_octave: int = 4) -> dict:
    """
    Parse note name to MIDI number and note type.
    
    Args:
        name: e.g. 'D4', 'G', 'F#', 'Bb', '-', '~', 'x'
        default_octave: octave if not specified (default 4)
        
    Returns:
        dict with keys: 'midi_number' (or None for rests), 'note_type'
        
    Raises:
        ValueError: if note name is invalid
        
    Examples:
        parse_note_name('D4') -> {'midi_number': 62, 'note_type': 'normal'}
        parse_note_name('D') -> {'midi_number': 62, 'note_type': 'normal'}
        parse_note_name('-') -> {'midi_number': None, 'note_type': 'rest'}
        parse_note_name('~') -> {'midi_number': None, 'note_type': 'ghost'}
    """
    name = name.strip()
    
    # Check for special symbols
    if name in SYMBOLS:
        return {"midi_number": None, "note_type": SYMBOLS[name]}
    
    # Parse regular notes
    # Only uppercase the first character (note letter); preserve the rest so
    # that lowercase 'b' flats (e.g. 'Db', 'Bb') are not converted to 'B'.
    note_char = name[0].upper()
    if note_char not in NOTE_NAME_TO_PC:
        raise ValueError(f"Invalid note: {name}")
    
    pitch_class = NOTE_NAME_TO_PC[note_char]
    remaining = name[1:]
    
    # Parse accidentals
    accidental_sum = 0
    idx = 0
    while idx < len(remaining) and remaining[idx] in SEMITONE_MODIFIERS:
        accidental_sum += SEMITONE_MODIFIERS[remaining[idx]]
        idx += 1
    
    pitch_class = (pitch_class + accidental_sum) % 12
    
    # Parse octave (if present)
    octave_str = remaining[idx:]
    if octave_str:
        try:
            octave = int(octave_str)
        except ValueError:
            raise ValueError(f"Invalid octave in note: {name}")
    else:
        octave = default_octave
    
    # Calculate MIDI number
    midi_number = 12 + (octave * 12) + pitch_class
    
    # Validate MIDI range
    if midi_number < 0 or midi_number > 127:
        raise ValueError(f"MIDI number {midi_number} out of range for note: {name}")
    
    return {"midi_number": midi_number, "note_type": "normal"}


def parse_notes_list(
    notes: list[str],
    default_octave: int = 4,
    infer_octave: bool = True
) -> list[dict]:
    """
    Parse list of note names.
    
    Args:
        notes: e.g. ['D', 'G', 'A', 'B', 'C']
        default_octave: starting octave if not specified
        infer_octave: if True, infer octave from previous note
        
    Returns:
        List of dicts with 'midi_number' and 'note_type'
    """
    result = []
    current_octave = default_octave
    
    for note_name in notes:
        note_data = parse_note_name(note_name, current_octave)
        
        # If inferring octave and the parsed note falls below the previous note,
        # bump the octave and re-parse so the *current* note uses the right octave.
        if infer_octave and note_data["note_type"] == "normal" and result:
            prev_midi = result[-1].get("midi_number")
            curr_midi = note_data["midi_number"]
            if prev_midi is not None and curr_midi is not None and curr_midi < prev_midi:
                current_octave += 1
                note_data = parse_note_name(note_name, current_octave)
        
        result.append(note_data)
    
    return result


def notes_to_pitches(notes_data: list[dict]) -> list[Pitch | None]:
    """
    Convert parsed notes to Pitch objects.
    
    Args:
        notes_data: list from parse_notes_list
        
    Returns:
        List of Pitch objects (or None for rests/ghost notes)
    """
    result = []
    for note_data in notes_data:
        if note_data["note_type"] == "normal" and note_data["midi_number"] is not None:
            result.append(Pitch.from_midi(note_data["midi_number"]))
        else:
            result.append(None)
    return result
