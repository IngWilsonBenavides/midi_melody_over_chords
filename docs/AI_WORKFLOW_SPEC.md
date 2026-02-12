# AI Workflow Specification: Melodic Dictation Generator

## Project Context
Build a MIDI melody generator over chord progressions for musical ear training (dictation exercises). Start with triadic arpeggios using quarter notes, designed to be extensible for future ML/genetic algorithm integration.

## Current Conversation Summary
- Language: Python
- Goal: Generate melodic dictations over chord progressions with configurable parameters
- Initial scope: Triadic arpeggios with quarter note subdivision
- Future roadmap: Add rhythmic variation, passing tones, Markov chains, genetic algorithms, ML models

## Critical Business Rules

### 1. MIDI Note Range
- **Range: MIDI 41 (F1) to MIDI 81 (A4)**
- This is NOT standard scientific pitch notation
- Verified from user's reference MIDI file: `01_midi_files/01_arpegios_Am_Am_Dm_Em.mid`

### 2. Voicing Rotation Algorithm (CORE LOGIC)
**This is the most important rule for generating non-repetitive melodies:**

For a progression with groups, each time a chord repeats, its voicing must "rotate up" by one scale degree:

**Example for C major chord (C E G) with sequence "1234":**
- Occurrence 1: G1 C1 E1 G2 → with "1234" → G1 C1 E1 G2
- Occurrence 2: C1 E1 G2 C2 → with "1234" → C1 E1 G2 C2  
- Occurrence 3: E1 G2 C2 E2 → with "1234" → E1 G2 C2 E2
- Occurrence 4: G2 C2 E2 G3 → with "1234" → G2 C2 E2 G3 (if G3 <= MIDI 81)

**Key principle:** The lowest note of the base voicing shifts up to the next chord tone each repetition, maintaining the 4-note pattern (root-third-fifth-root).

**With sequence "4321" (reverse):**
- Occurrence 1: G1 C1 E1 G2 → with "4321" → G2 E1 C1 G1
- Occurrence 2: C1 E1 G2 C2 → with "4321" → C2 G2 E1 C1

### 3. Sequence Patterns
- Format: 4-digit string using digits 1-4, each appearing exactly once
- "1234" = ascending order (lowest to highest pitch)
- "4321" = descending order (highest to lowest pitch)
- "1243" = lowest, 2nd, highest, 3rd
- Must be a permutation of "1234"

### 4. Musical Theory
- Tonality: Major and minor scales
- Chord degrees: Roman numerals (I, ii, iii, IV, V, vi, vii°)
  - Uppercase = major chord
  - Lowercase = minor chord
- Triads only (root, third, fifth)
- All chords diatonic to the key

## Configuration Schema (YAML)

```yaml
key: C                      # Tonic: C, D, E, F, G, A, B (add m for minor: Am, Dm, etc.)
progression: [I, iv, iii, V]  # Roman numeral chord degrees
groups: 4                   # Number of times to repeat the progression
subdivision: quarter        # Note duration (quarter for now, eighth/half future)
sequence: "4321"           # Permutation of 1234
range: [41, 81]            # MIDI note range (F1 to A4)
tempo: 100                 # BPM
ppqn: 480                  # Pulses per quarter note (MIDI resolution)
```

## Expected Input/Output Examples

### Example 1: Simple progression
**Input:**
```yaml
key: C
progression: [I, iv]
groups: 2
subdivision: quarter
sequence: "1234"
range: [41, 81]
tempo: 100
```

**Output (human-readable notes per measure):**
```
Measure 1 (C): G1 C1 E1 G2
Measure 2 (Am): A1 C1 E1 A2
Measure 3 (C): C1 E1 G2 C2
Measure 4 (Am): C1 E1 A2 C2
```

### Example 2: With sequence variation
**Input:**
```yaml
key: C
progression: [I, iv]
groups: 2
sequence: "1243"  # Note the different pattern
```

**Output:**
```
Measure 1 (C): G1 C1 G2 E1
Measure 2 (Am): A1 C1 A2 E1
Measure 3 (C): C1 E1 C2 G2
Measure 4 (Am): C1 E1 C2 A2
```

## Architecture Design

### Directory Structure
```
/dictados/
  pyproject.toml
  README.md
  config.yaml              # User configuration file
  src/
    dictados/
      __init__.py
      main.py              # Entry point
      config.py            # Pydantic models for validation
      domain/
        __init__.py
        pitch.py           # Pitch class (MIDI number wrapper)
        note.py            # Note class (pitch + timing)
        chord.py           # Chord class (root + quality)
        scale.py           # Scale class (tonic + mode)
        phrase.py          # Phrase and Measure classes
      generators/
        __init__.py
        progression.py     # Expand chord progression
        voicing.py         # VoicingEngine (CORE: rotation algorithm)
        sequence.py        # SequenceApplicator (apply patterns)
        rhythm.py          # RhythmEngine (subdivision to ticks)
        phrase_builder.py  # PhraseBuilder (orchestrates everything)
      validation/
        __init__.py
        spec_validator.py  # Validate input configuration
      midi/
        __init__.py
        exporter.py        # MidiExporter (write MIDI files)
  tests/
    test_pitch.py
    test_chord.py
    test_scale.py
    test_voicing.py        # TEST THE ROTATION ALGORITHM
    test_sequence.py
    test_progression.py
    test_phrase_builder.py
```

### Key Classes and Methods

#### 1. domain/pitch.py
```python
class Pitch:
    midi_number: int  # 41-81 range
    
    @staticmethod
    def from_midi(midi: int) -> Pitch:
        """Create from MIDI number, validate range"""
    
    def __hash__(self) -> int:
        """Enable use in sets/dicts"""
    
    def __lt__(self, other) -> bool:
        """Enable sorting"""
```

#### 2. domain/chord.py
```python
class Chord:
    root: Pitch
    quality: ChordQuality  # Enum: MAJOR, MINOR
    inversion: int = 0
    
    def get_triad_pitches(self, lowest_pitch: Pitch) -> list[Pitch]:
        """Return [root, third, fifth] starting from lowest_pitch
        Returns exactly 4 pitches in ascending order: 
        [lowest, next_tone, third_tone, lowest+octave]
        """
```

#### 3. generators/voicing.py
```python
class VoicingEngine:
    """CORE CLASS: Implements voicing rotation algorithm"""
    
    def __init__(self, range_low: Pitch, range_high: Pitch):
        self._range = (range_low, range_high)
        self._voicing_state: dict[Chord, int] = {}  # Track repetition count
    
    def get_next_voicing(self, chord: Chord) -> list[Pitch]:
        """Returns next voicing for chord using rotation algorithm
        
        Tracks how many times this chord has been used and returns
        the appropriate rotation:
        - Call 1: Start from lowest possible position
        - Call 2: Rotate up by one chord tone
        - Call 3: Rotate up again
        - etc.
        
        Returns list of 4 Pitch objects in ascending order
        """
```

#### 4. generators/phrase_builder.py
```python
class PhraseBuilder:
    """Orchestrates the generation of complete phrases"""
    
    def __init__(
        self, 
        voicing_engine: VoicingEngine,
        rhythm_engine: RhythmEngine
    ):
        pass
    
    def build_phrase(
        self,
        chords: list[Chord],
        pattern: str,
        subdivision: Subdivision,
        time_signature: TimeSignature
    ) -> Phrase:
        """Main generation workflow:
        1. For each chord, get voicing from voicing_engine
        2. Apply sequence pattern with SequenceApplicator
        3. Convert to Notes with timing from rhythm_engine
        4. Group into Measures based on time_signature
        5. Return complete Phrase
        """
```

#### 5. main.py
```python
def generate_dictation(config_path: Path, output_path: Path) -> None:
    """Main entry point
    
    Workflow:
    1. Load and parse YAML config
    2. Validate configuration
    3. Build Scale from key
    4. Generate chord progression from degrees
    5. Initialize VoicingEngine with range
    6. Build Phrase using PhraseBuilder
    7. Export to MIDI file
    """
```

## Test Strategy

### Critical Tests (Must Pass)

#### test_voicing.py
```python
def test_voicing_rotation_basic():
    """Test that C major chord rotates correctly over 4 repetitions"""
    # Setup
    engine = VoicingEngine(Pitch.from_midi(41), Pitch.from_midi(81))
    chord = Chord(root=Pitch.from_midi(48), quality=ChordQuality.MAJOR)  # C
    
    # Test
    v1 = engine.get_next_voicing(chord)
    v2 = engine.get_next_voicing(chord)
    v3 = engine.get_next_voicing(chord)
    
    # Assert
    assert v1 == [G1, C1, E1, G2]  # First voicing starts lowest
    assert v2 == [C1, E1, G2, C2]  # Rotated up
    assert v3 == [E1, G2, C2, E2]  # Rotated up again

def test_sequence_application():
    """Test that sequence '4321' correctly reverses order"""
    notes = [Pitch(43), Pitch(48), Pitch(52), Pitch(55)]  # G1,C1,E1,G2
    result = SequenceApplicator.apply_pattern(notes, "4321")
    assert result == [Pitch(55), Pitch(52), Pitch(48), Pitch(43)]

def test_full_generation():
    """End-to-end test matching user's example"""
    spec = DictationSpec(
        key="C",
        progression=["I", "iv"],
        groups=2,
        sequence="1234",
        # ... other params
    )
    phrase = generate_phrase(spec)
    
    # Verify measure 1
    assert phrase.measures[0].notes[0].pitch.midi_number == 43  # G1
    assert phrase.measures[0].notes[1].pitch.midi_number == 48  # C1
    # ... verify all expected notes
```

### Additional Tests
- `test_pitch.py`: Range validation, MIDI conversion
- `test_chord.py`: Triad generation, degree parsing
- `test_scale.py`: Diatonic chords, key signatures
- `test_progression.py`: Repetition, expansion
- `test_midi_exporter.py`: MIDI file structure validation

## Development Workflow

### Phase 1: Foundation (Start Here)
1. Create project structure with pyproject.toml
2. Implement domain models (Pitch, Note, Chord, Scale)
3. Write tests for domain models
4. Implement Scale.from_string() and chord generation

### Phase 2: Core Generation
1. **Implement VoicingEngine with rotation algorithm** (MOST CRITICAL)
2. Write extensive tests for voicing rotation
3. Implement SequenceApplicator
4. Implement RhythmEngine (basic quarter notes)
5. Test each component independently

### Phase 3: Integration
1. Implement PhraseBuilder
2. Implement ProgressionGenerator
3. Write integration tests
4. Test full workflow with user's examples

### Phase 4: I/O
1. Implement DictationSpec with Pydantic
2. Add YAML config parsing
3. Implement MidiExporter using mido or pretty_midi
4. Generate test MIDI files
5. Verify output in DAW/Guitar Pro

### Phase 5: Validation
1. Compare generated MIDI with user's reference file
2. Test all example configurations
3. Document edge cases and limitations

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
pydantic = "^2.0"
pyyaml = "^6.0"
mido = "^1.3"  # or pretty-midi
pytest = "^7.0"
```

## Future Extensions (Post-MVP)

### Rhythmic Expansion
- Add Subdivision enum: EIGHTH, HALF, DOTTED_QUARTER
- Support mixed rhythms within measures
- Implement rest insertion
- Add ties and syncopation

### Melodic Sophistication
- Passing tones (diatonic and chromatic)
- Neighbor tones
- Appoggiatura
- Escape tones

### Generative Algorithms
- Markov chains for note-to-note transitions
- Genetic algorithms with fitness functions:
  - Melodic smoothness (prefer small intervals)
  - Tension/resolution (dissonance on weak beats)
  - Variety (avoid excessive repetition)
  - Direction (prefer arcs over zigzag)

### Machine Learning
- Seq2seq models for chord-to-melody generation
- Train on jazz standards corpus
- Use Magenta's models as reference
- Implement with PyTorch or TensorFlow

## AI Agent Instructions

When implementing this project:

1. **Start with tests**: Write failing tests first for each component
2. **Focus on VoicingEngine**: This is the unique core logic - get it perfect
3. **Validate constantly**: After each component, run tests and verify output
4. **Use user's examples**: The examples in this document are ground truth
5. **Ask before deviating**: If the rotation algorithm seems wrong, verify with user first
6. **Generate actual MIDI**: Don't just print notes - write files user can play
7. **Document assumptions**: When making decisions, document why
8. **Keep it simple**: Resist over-engineering - YAGNI principle

## Verification Checklist

Before considering the project complete:

- [ ] All tests pass
- [ ] Generated MIDI matches user's examples exactly
- [ ] Configuration validation works (rejects invalid input)
- [ ] MIDI files play correctly in Guitar Pro / DAW
- [ ] Code is documented with docstrings
- [ ] README.md explains usage with examples
- [ ] Edge cases handled (range limits, invalid degrees)
- [ ] Performance acceptable (generates instantly)

## Contact Points / Clarifications Needed

If implementing this and you encounter:
- **Ambiguous voicing behavior**: Verify rotation algorithm with user
- **MIDI note number confusion**: Use MIDI 41-81, not standard scientific notation
- **Chord quality ambiguity**: Use upper/lowercase Roman numerals (I=major, i=minor)
- **Rhythm representation**: For now, all notes are quarter notes (480 ticks at PPQN=480)

## Example Session

```bash
# Create config
$ cat config.yaml
key: C
progression: [I, iv, iii, V]
groups: 4
subdivision: quarter
sequence: "4321"
range: [41, 81]
tempo: 100

# Generate dictation
$ python -m dictados config.yaml output.mid
Generated: output.mid (16 measures, 64 notes)

# Verify
$ open output.mid  # Opens in default MIDI player
```

---

**This specification should enable an AI agent to implement the complete system from scratch while maintaining consistency with all design decisions made in this conversation.**
