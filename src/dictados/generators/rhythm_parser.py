"""
Rhythm notation parser.
Converts musical notation (q, e, h, etc.) to MIDI ticks.
"""

from __future__ import annotations


# Mapping musical notation to relative beat values
# Based on quarter note = 1 beat
NOTATION_TO_BEATS = {
    "w": 4.0,      # whole
    "wd": 6.0,     # whole dotted
    "h": 2.0,      # half
    "hd": 3.0,     # half dotted
    "q": 1.0,      # quarter
    "qd": 1.5,     # quarter dotted
    "e": 0.5,      # eighth
    "ed": 0.75,    # eighth dotted
    "s": 0.25,     # sixteenth
    "sd": 0.375,   # sixteenth dotted
}


def rhythm_to_ticks(notation: str, ppqn: int) -> int:
    """
    Convert single rhythm notation to MIDI ticks.
    
    Args:
        notation: e.g. 'q', 'e', 'hd', 'qd'
        ppqn: parts per quarter note (MIDI resolution)
        
    Returns:
        Duration in ticks
        
    Raises:
        ValueError: if notation is not recognized
    """
    notation = notation.strip().lower()
    
    if notation not in NOTATION_TO_BEATS:
        raise ValueError(f"Unknown rhythm notation: {notation}")
    
    beats = NOTATION_TO_BEATS[notation]
    ticks = int(beats * ppqn)
    return ticks


def parse_rhythm_list(notes: list[str], ppqn: int) -> list[int]:
    """
    Convert list of rhythm notations to ticks.
    
    Args:
        notes: e.g. ['q', 'e', 'e', 'e', 'e']
        ppqn: parts per quarter note
        
    Returns:
        List of durations in ticks
        
    Raises:
        ValueError: if any notation is invalid
    """
    return [rhythm_to_ticks(notation, ppqn) for notation in notes]


def validate_rhythm_for_measure(
    rhythms: list[str],
    time_signature: str,
    ppqn: int
) -> bool:
    """
    Validate that rhythm fits within time signature.
    
    Args:
        rhythms: list of rhythm notations
        time_signature: e.g. '3/4', '4/4'
        ppqn: parts per quarter note
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    numerator, denominator = map(int, time_signature.split("/"))
    
    # Calculate expected measure ticks
    # In 3/4: 3 quarter notes = 3 * ppqn ticks
    measure_ticks = (numerator * ppqn * 4) // denominator
    
    # Calculate actual ticks from rhythms
    actual_ticks = sum(rhythm_to_ticks(r, ppqn) for r in rhythms)
    
    if actual_ticks != measure_ticks:
        raise ValueError(
            f"Rhythm total {actual_ticks} ticks does not match "
            f"measure {measure_ticks} ticks for {time_signature}"
        )
    
    return True
