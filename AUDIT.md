# Auditoría Técnica — `midi_melody_over_chords`

> Fecha: 2026-04-29 | Auditor: GitHub Copilot Agent  
> Alcance: calidad de código, robustez, edge cases, arquitectura, tests, ML, escalabilidad

---

## Resumen ejecutivo

El proyecto tiene una arquitectura **bien estructurada** para su tamaño: dominio musical limpio, estrategias
intercambiables, exportador MIDI funcional y 325 tests pasando. Sin embargo, hay **fallas concretas** que deben
corregirse antes de escalar a más features — en particular un bug crítico de regresión silenciosa de acordes,
una división por cero, y una feature publicitada (`--style`) que no está cableada.

---

## Hallazgos — Lista priorizada

### 🔴 CRITICAL

| # | Dónde | Hallazgo | Evidencia |
|---|-------|----------|-----------|
| C1 | `improviser/main.py:251` | **`--style` se parsea pero nunca se usa.** La bandera existe en CLI y en `ParsedProgression`, pero `generate_improvisation()` no acepta `style` y `ImproEngine` no lo recibe. El usuario ve en la ayuda 7 estilos disponibles, pero todos producen salida idéntica. | `grep -n style main.py` — `args.style` leído pero no pasado a ninguna función |
| C2 | `midi/exporter.py` + `main.py:260` | **ZeroDivisionError con `--tempo 0`**. `mido.bpm2tempo(0)` lanza `ZeroDivisionError` sin capturar. | `python3 -c "import mido; mido.bpm2tempo(0)"` → `ZeroDivisionError: float division by zero` |
| C3 | `improviser/theory.py:25` | **`make_pitch()` bypassa el range-guard de `Pitch`.** `Pitch.from_midi()` valida el rango 41–81; `make_pitch()` construye directamente `Pitch(midi_number=midi)` sin validación, permitiendo MIDI inválidos (usado para el rango extendido 48–84 del improvisador). Esto es un contrato roto: la clase `Pitch` documenta `MIN_MIDI=41, MAX_MIDI=81`, pero el improvisador opera en 48–84 sin que la abstracción lo sepa. |

### 🟠 HIGH

| # | Dónde | Hallazgo | Evidencia |
|---|-------|----------|-----------|
| H1 | `improviser/engine.py:73` | **Dead code: `strategies, weights = zip(*_STRATEGY_POOL)`**. La línea 73 asigna variables que nunca se usan; la lógica real crea pools locales en cada iteración del bucle. Confunde al lector y desperdicia ciclos en cada `improvise()`. | Comprobado: `strategies` y `weights` no se usan después de línea 73 |
| H2 | `improviser/theory.py:98` | **Slash chords (`Am/E`), `aug`, `sus4`, `dim7`, `m7b5` se degradan silenciosamente a MAJOR.** `parse_chord_name('Am/E')` devuelve MAJOR en lugar de MINOR. `Edim7`, `Faug`, `Csus4`, `G#m7b5` también. El fallback `quality = ChordQuality.MAJOR` es silencioso — no hay advertencia al usuario. | `parse_chord_name('Am/E').quality == MAJOR` (debería ser MINOR) |
| H3 | `improviser/text_parser.py:113` | **Silencio en fallo de parseo de acorde individual.** `except ValueError: pass` descarta tokens sin loguear ni advertir. Si el usuario escribe `"Am Xyz C Dm"`, `Xyz` desaparece sin aviso. | Línea 113 en text_parser.py |
| H4 | `engine.py:80–95` | **Nuevas instancias de estrategias creadas en cada medida de cada llamada a `improvise()`.** Seis objetos instanciados × N medidas = O(N) allocations innecesarias en progresiones largas. | `LickStrategy(), ScaleWalkStrategy()...` dentro del bucle `for i, chord` |
| H5 | `improviser/midi_chord_reader.py` | **`OSError` de mido no capturado para MIDIs corruptos.** Un fichero `.mid` mal formado lanza `OSError: MThd not found` directamente al usuario sin mensaje amigable. | Reproducido con fichero corrupto |

### 🟡 MEDIUM

| # | Dónde | Hallazgo | Evidencia |
|---|-------|----------|-----------|
| M1 | `main.py:48` | **Output dir relativo `01_midi_files/output/`**. Si el CLI se invoca desde un directorio distinto al repo root, el fichero se crea en un lugar inesperado. No se informa al usuario dónde está el directorio de salida. | `Path("01_midi_files") / "output"` — siempre relativo al CWD |
| M2 | `text_parser.py:_BPM_RE` | **BPM regex solo acepta 2–3 dígitos** (`\d{2,3}`), ignorando "9bpm" o "1200bpm". Además no hay validación del rango; se acepta "999bpm" o "0bpm" sin error. MIDI tempo es un valor 24-bit (máx. 16,777,215 μs → min. ~4 BPM). | `parse_text("9bpm Am C")` → usa 120 por defecto en silencio |
| M3 | `pyproject.toml` | **`pydantic` declarado como dependencia de runtime pero solo se usa en `config.py` (original generator)**. El improvisador no usa pydantic. En un futuro sin el generador original, pydantic sería una dependencia inútil. | `grep -rn pydantic src/` |
| M4 | `improviser/engine.py` | **`ImproEngine.improvise()` no es idempotente con la misma semilla**: dos llamadas consecutivas con la misma instancia producen resultados distintos porque el `_rng` avanza. | `r1 = e.improvise(chords); r2 = e.improvise(chords) → r1 != r2` |
| M5 | `ml/` fuera de `src/` | **`ml/` y `tools/` viven fuera de `src/`**, rompiendo la convención `src/` layout. `ml/train.py` hace `sys.path.insert(0, str(_REPO_ROOT / "src"))` manualmente para compensar. | `ml/train.py:9-10` |
| M6 | `improviser/midi_chord_reader.py` | **Chord detection falla silenciosamente** para medidas vacías: devuelve el acorde anterior (o C major si es la primera). No hay advertencia cuando el 50%+ de medidas usa fallback. | `chord = chords[-1] if chords else Chord(root=make_pitch(60), quality=MAJOR)` |
| M7 | `improviser/` | **Sin logging estructurado**. Todo usa `print()`. En uso programático (p.ej. integrado en DAW plugin o servidor), los prints van a stdout sin control de nivel. No hay forma de silenciar el output informativo. | `grep -n print main.py` → 9 prints |
| M8 | `pyproject.toml` | **Sin herramientas de dev (ruff, mypy, black)**. No hay linter ni type-checker configurado. | `pyproject.toml` — solo `pytest` como dev dep |

### 🔵 LOW

| # | Dónde | Hallazgo | Evidencia |
|---|-------|----------|-----------|
| L1 | `phrase_library.py` | **Lick #7 dura 3.5 beats** (7 notas × 0.5 = 3.5 ≠ 4.0). **CORREGIDO** al verificar: todos los licks suman exactamente 4.0. ✅ | — |
| L2 | `domain/pitch.py` | **`MIN_MIDI=41, MAX_MIDI=81` son constantes sin contexto**. No está documentado por qué 41 y no 48 (C3). | `pitch.py:5-6` |
| L3 | `improviser/chord_track.py` | **`CHORD_TRACK_PROGRAM = 0`** documentado pero el valor se ignora — `export_two_track` pasa `accompaniment_program=0` hardcoded. | `main.py:258` → `accompaniment_program=0` |
| L4 | `improviser/strategies/` | **Typo en nombre de módulo**: `arpegio.py` debería ser `arpeggio.py` (dos 'g'). Menor, pero inconsistente con el resto. | `ls src/dictados/improviser/strategies/` |
| L5 | `tools/dataset/splitter.py` | **`n_val` puede ser 0** si `n * val_ratio < 0.5`. Con datasets pequeños de 1–2 ficheros fuente, val y test quedan vacíos. | Sin assert mínimo de tamaño |
| L6 | `improviser/main.py` | **Archivo YAML de temp** (`temp_am_g_f_g.yaml`) en la raíz del repo, claramente olvidado. | `ls` en root |
| L7 | `ml/model/ngram.py` | **TODO pendiente**: `# TODO: replace this file with gru.py` — doc de intención sin issue/ticket asociado. | `ngram.py:28` |

---

## Análisis por área

### 1. Arquitectura y módulos

**Bien**: dominio (`Chord`, `Note`, `Phrase`, `Pitch`) correctamente separado del IO. Estrategias
son intercambiables vía la ABC `ImproStrategy`. El flujo `text → chords → engine → MIDI` es limpio.

**Problemas**: `ml/` y `tools/` fuera de `src/` rompe la convención de layout. `make_pitch()` existe para
saltarse la validación de `Pitch` — señal de que los rangos de dominio y del improvisador deberían ser
configurables o que `Pitch` debería aceptar el rango extendido. El acoplamiento entre `engine.py` y
`theory.py` (importa `IMPRO_MIN_MIDI`, `IMPRO_MAX_MIDI` directamente) es aceptable pero podría centralizarse.

### 2. CLI y UX

**Problemas**:
- `--style` documentado y parseado pero **sin efecto real** (bug C1).
- `--tempo 0` crashea con ZeroDivisionError (bug C2).
- No hay validación de rango en `--tempo` ni en `--rounds` (rounds=0 generaría 0 compases).
- Output path relativo, difícil de predecir si se invoca desde otro directorio.

### 3. Correctitud musical y edge cases

- **Acordes no reconocidos**: slash chords (`Am/E`) degradan a MAJOR silenciosamente. Sus4, aug, dim7 igual.
- **Progresiones vacías**: `improvise([])` devuelve `[]` silenciosamente — OK.
- **Compás odd**: solo se valida 4/4 en práctica; `build_chord_track` acepta `time_sig_num` pero no hay
  tests con 3/4 o 6/8.
- **Notas superpuestas**: el exporter acumula `note_on` / `note_off` en orden tick, pero la frase de acordes
  produce N notas simultáneas en start_tick idéntico — esto es correcto MIDI polifónico y funciona bien.
- **Rests**: `Note.note_type='rest'` existe pero ninguna estrategia los produce. El ML model tiene
  `rest_prob_boost` pero el pipeline de inferencia del improvisador no usa el ML model.

### 4. Dataset / ML

- **Determinismo correcto**: splitter por fichero fuente evita leakage ✅.
- **ML model y improviser desconectados**: `ml/infer.py` genera MIDI de forma independiente; el `ImproEngine`
  nunca usa el modelo entrenado. Son dos sistemas paralelos sin puente.
- **pickle sin versión**: `ngram.pkl` usa `protocol=4` pero no guarda versión del formato — cambios de
  esquema rompen modelos guardados silenciosamente.
- **`_STRATEGY_POOL` deadcode** en engine (H1).

### 5. Testing

**Cobertura actual**: 325 tests, todos pasando. Cubre dominio, estrategias, integración, ML.  
**Gaps**:
- No hay test de CLI end-to-end (`subprocess` o `CliRunner`).
- No hay test de que `--style` cambie el output (porque aún no está implementado).
- No hay test de BPM=0 ni BPM=999.
- No hay test de `Am/E` slash chord.
- No hay golden test de eventos MIDI (comparar byte-a-byte o por eventos).
- No hay test de progresión muy larga (100+ medidas) para performance.

### 6. Python buenas prácticas

- `from __future__ import annotations` consistente ✅.
- Typing bien usado en dominio y estrategias ✅.
- Sin logging, todo `print()` — no apto para uso programático.
- `pydantic` como dep de runtime pero solo en el generador original.
- Sin `ruff`/`mypy`/`black` configurados.
- Typo: `arpegio.py` → `arpeggio.py`.

### 7. Performance y escalabilidad

- **O(N) strategy allocations**: para una progresión de 100 compases, se crean ~600 objetos de estrategia.
  Costo bajo ahora, innecesario.
- **`ImproEngine` no es idempotente** (M4): para cachear o testear hay que crear nuevas instancias.
- **Dataset**: sin caché de ficheros ya procesados — reprocesa todo en cada ejecución.
- **Paralelismo**: `build_dataset.py` procesa MIDIs secuencialmente; trivialmente paralelizable con
  `concurrent.futures.ProcessPoolExecutor`.

### 8. Seguridad / robustez

- `OSError` de mido en MIDIs corruptos no capturado (H5).
- `ZeroDivisionError` con BPM=0 (C2).
- Sin validación de `--rounds` (0 o negativo).
- Ficheros de salida se crean con paths relativos — no vulnerable, pero confuso.

---

## Plan de refactor

### Fase 1 — Quick Wins (1–2 días)

Estos cambios son seguros, no rompen la API/CLI, y se pueden hacer en commits pequeños:

| # | Tarea | Archivo(s) | Tipo |
|---|-------|-----------|------|
| QW1 | Eliminar dead code `strategies, weights` en engine | `engine.py:73` | Limpieza |
| QW2 | Añadir validación de `--tempo` (rango 1–300) y `--rounds` (≥1) en CLI | `main.py` | Robustez |
| QW3 | Capturar `OSError`/`ValueError` de mido en `midi_chord_reader.py` | `midi_chord_reader.py` | Robustez |
| QW4 | Loguear (warning) acordes que no se reconocen en `text_parser.py` | `text_parser.py` | UX |
| QW5 | Corregir slash-chord: stripear `/bass` antes de parsear, warning para `aug`/`sus` | `theory.py` | Correctitud |
| QW6 | Añadir `logging` básico en `main.py` (nivel INFO/WARNING) manteniendo prints para terminal | `main.py` | Mantenibilidad |
| QW7 | Eliminar `temp_am_g_f_g.yaml` y limpiar root del repo | root | Limpieza |
| QW8 | Añadir tests para: BPM=0, slash chords, acorde desconocido, MIDI corrupto | `tests/` | Testing |
| QW9 | Registrar el typo `arpegio` → `arpeggio` como alias en `__init__.py` (sin renombrar aún para no romper imports) | `strategies/__init__.py` | Limpieza |
| QW10 | Añadir `ruff` y `mypy` a `[project.optional-dependencies]` en pyproject.toml | `pyproject.toml` | Dev tooling |

### Fase 2 — Hardening + Scale (1–2 semanas) ← **Requiere tu OK**

Estos cambios tienen mayor alcance:

| # | Tarea | Impacto |
|---|-------|---------|
| S1 | **Cablear `--style` al engine**: pasar `style` a `ImproEngine`, que seleccione pools de estrategias distintos según estilo (swing → más approachTone, latin → más lick+arpeggio, blues → escala blues, etc.) | HIGH — la feature principal que falta |
| S2 | **Resolver dualidad de rango `Pitch`**: introducir `MELODY_MIDI_RANGE = (48, 84)` como constante de configuración o ampliar `Pitch` para que acepte rango configurable | MED |
| S3 | **Conectar ML model al ImproEngine**: añadir `MLStrategy` que use `ChordConditionedNGram.sample_next()` como una estrategia más del pool | HIGH |
| S4 | **Humanización básica**: añadir variación de timing (±5–10 ticks) y velocidad (±10%) controlada por estilo | MED |
| S5 | **Mover `ml/` y `tools/` bajo `src/`** o establecer layout explícito en `pyproject.toml` | LOW — solo organización |
| S6 | **Paralelizar dataset builder** con `ProcessPoolExecutor` | LOW/MED |
| S7 | **Versionar pickle del modelo** (añadir campo `schema_version`) | MED |
| S8 | **Tests golden de MIDI**: comparar eventos MIDI con snapshot para detectar regresiones musicales | MED |
| S9 | **Soporte de compases 3/4 y 6/8** en el engine e improvisador | MED |

---

## Skills / Capacidades para música generativa seria

| Skill | Impacto | Dificultad | Integración |
|-------|---------|------------|-------------|
| **1. Humanización controlada** (timing/velocity micro-variación por estilo) | 🔴 Alto | Baja | Añadir capa de post-proceso en `melody_builder.py` después de construir la frase; `--humanize 0.0–1.0` |
| **2. Swing & groove templates** (swing ratio configurable, dotted-eighth feel) | 🔴 Alto | Media | Nueva función en `ImproEngine._apply_groove()` que retarda eventos pares en swing ratio; activado por `style="swing"` |
| **3. Call/Response musical real** (el engine ya lo intenta, pero sin restricciones de fraseo real) | 🟠 Medio | Media | Mejorar la lógica de `is_call` en engine: "call" termina en tensión (no chord-tone), "response" resuelve; estado entre medidas |
| **4. Conditioning por estilo en ML** (`style_tag` en NGram ya existe como slot vacío) | 🔴 Alto | Media | Activar el `style_tag` en `ChordConditionedNGram` — el slot ya existe en el código pero está marcado como `# noqa` |
| **5. Evaluación automática** (métricas: densidad de notas, % chord tones, intervalos medios, comparación A/B) | 🟠 Medio | Baja | Nuevo módulo `tools/analysis/melody_metrics.py`; integrar en pipeline CI |
| **6. Export más completo** (CC de expresión/sustain, articulaciones, multi-instrumento) | 🟡 Bajo | Media | Extender `MidiExporter` con mensajes CC y el concepto de instrumento por pista |
| **7. Plugin de estrategias externas** (que el usuario pueda registrar sus propias) | 🟡 Bajo | Alta | Entry-points de setuptools o simple `importlib` registry |
| **8. Pipeline de dataset robusto** (deduplicación por hash, caché incremental, validación de licencias) | 🟠 Medio | Media | Añadir `hashlib.md5` fingerprint por fichero en `build_dataset.py`; skip si ya procesado |
| **9. Soporte de compases irregulares** (3/4, 6/8, 5/4) | 🟡 Bajo | Media | Parametrizar `measure_ticks` y ajustar ritmos en estrategias |
| **10. Generación condicionada por mood/key** (indicar tonalidad explícita y que el engine la respete) | 🟠 Medio | Alta | Ampliar `theory.py` con contexto de tonalidad; estrategias ponderan notas de la escala global |

---

## Veredicto general

El código **es bueno para su etapa**: legible, testeado, con abstracciones correctas. Los riesgos principales son:
1. Un bug de UX grave (style no implementado) que erosiona la confianza del usuario.
2. Dos crasheos sin capturar (BPM=0, MIDI corrupto).
3. Un fallo de correctitud silencioso (slash/aug/sus → MAJOR).

Los Quick Wins (Fase 1) se pueden hacer sin romper nada en un día. La Fase 2 (cablear style, ML, humanización) requiere diseño más cuidadoso y tu aprobación explícita.

---

*Este documento fue generado a partir de inspección estática y pruebas dinámicas del código.*
