# Manual de Códigos - Dictados

Este manual resume cómo ejecutar **todas las funcionalidades disponibles hasta ahora** en el proyecto.

## 1) Preparar entorno (PowerShell)

Desde la raíz del proyecto:

```powershell
& .\.venv\Scripts\Activate.ps1
```

Si aún no tienes dependencias instaladas:

```powershell
python -m pip install -e .
python -m pip install -e .[test]
```

---

## 2) Generar MIDI desde YAML de configuración (modo app original)

### 2.1 Usar `config.yaml`

```powershell
python -m dictados.main config.yaml
```

### 2.2 Usar una melodía específica (ejemplo Bach)

```powershell
python -m dictados.main bach_minuet_3.yaml
```

Salida esperada: archivo `.mid` en `01_midi_files/output/` con nombre autogenerado.

---

## 3) Importar MIDI de `input` con el motor propio y generar derivados

Procesa todos los `.mid` en `01_midi_files/input/` y genera:

- `*_engine.yaml` (original, minimalista)
- `*_to_C_major.yaml` (melodía transpuesta, minimalista)
- `*_to_C_major.mid` (MIDI transpuesto)

Comando:

```powershell
python -c "from dictados.midi.pipeline import process_input_midis; print(process_input_midis())"
```

Rutas de salida:

- YAML: `01_midi_files/generated_files_yaml/`
- MIDI transpuesto: `01_midi_files/output/transposed_c_major/`

---

## 4) Formato YAML minimalista actual

Los YAML generados por importación MIDI ahora se exportan solo con:

- `key`
- `time_signature`
- `tempo_bpm`
- `ppqn`
- `program`
- `melody`

Ejemplo de bloque:

```yaml
key: G
time_signature: 3/4
tempo_bpm: 120
ppqn: 480
program: 30
melody:
- compas: 1
  notes: [D, G, A, B, C]
  rhythm: [q, e, e, e, e]
```

---

## 5) Ejecutar tests

### 5.1 Tests del módulo MIDI nuevo

```powershell
python -m pytest tests/test_midi_importer.py tests/test_midi_pipeline.py
```

### 5.2 Suite completa

```powershell
python -m pytest
```

Nota: pueden existir fallos previos en módulos no relacionados al pipeline MIDI.

---

## 6) Limpieza y regeneración de YAML `*_engine.yaml`

Borrar y volver a generar:

```powershell
Get-ChildItem -Path "01_midi_files/generated_files_yaml" -Filter "*_engine.yaml" | Remove-Item -Force
python -c "from dictados.midi.pipeline import process_input_midis; print(process_input_midis())"
```

---

## 7) Funcionalidades disponibles hoy

1. Generación de dictados por especificación YAML (progresiones o melodía explícita).
2. Exportación MIDI desde el motor interno.
3. Importación MIDI al motor interno (`Phrase/Measure/Note`).
4. Detección de metadatos MIDI (tempo, compás, armadura).
5. Transposición automática a C mayor (con fallback por histograma de pitch class).
6. Exportación de YAML minimalista para dataset.
7. Exportación de MIDI transpuesto a C mayor.

---

## 8) Respuesta rápida a duda frecuente

**¿Los `.yaml` se crean cuando ejecuto la app con un `.mid` o los crea Copilot manualmente?**

Se crean al ejecutar el pipeline del proyecto (motor):

```powershell
python -c "from dictados.midi.pipeline import process_input_midis; print(process_input_midis())"
```
