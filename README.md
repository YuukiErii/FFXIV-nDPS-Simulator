# FFXIV SIM Workspace

This folder is organized around two local tools and one skill-line archive.

- `releases/windows/`: user-facing portable executables and their short usage notes.
- `src/`: source code for the XIV in the Shell TTS converter.
- `scripts/`: reproducible build/data-generation scripts.
- `data/`: FF14 Chinese-English skill mapping files used by the converter.
- `examples/skill_lines/`: saved XIV in the Shell exports, converted Chinese CSVs, TTS skill-line txt files, and merged timeline outputs.
- `src/ffxiv_ndps_simulator/`: the DPS simulator source, assets, and versioned executables.
- `docs/`: older notes that are useful for context but not part of the active converter.
- `artifacts/specs/`: PyInstaller spec files. Local build cache, reference checkouts, duplicates, and legacy binaries stay under `artifacts/` but are ignored by Git.

Main executables:

```text
releases/windows/xiv_shell_tts.exe
releases/windows/ffxiv_personal_ndps.exe
```

The executable converts XIV in the Shell CSV exports into the old `TTS.py` txt format. It can also take an optional fight timeline txt and produce the old `MERGE.PY`-style merged timeline output.

`ffxiv_personal_ndps.exe` opens the personal nDPS simulator GUI. It also supports `--self-test`, which verifies packaged resources, 13 DPS smoke CSVs, historical target-data samples, the formula layer, and the bundled `ama_xiv_combat_sim` dependency.

Rebuild command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_xiv_shell_tts_exe.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_ffxiv_ndps_simulator_exe.ps1
```

Simulator source entrypoint:

```powershell
.\.venv\Scripts\python.exe .\src\ffxiv_ndps_simulator\sim.py
```

`src\ffxiv_ndps_simulator\sim_test.py` is now only a compatibility launcher that forwards to the unified `sim.py` GUI. The simulator report can export a Markdown summary plus CSV detail files for combat log, skill aggregation, coverage, resource warnings, and metadata.
