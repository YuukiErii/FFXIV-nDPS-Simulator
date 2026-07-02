# FFXIV SIM Workspace

This repository contains the personal nDPS simulator, the modern desktop UI track, the XIV in the Shell TTS converter, and the sample skill-line archive.

Active docs:

- User manual: `docs/USER_MANUAL.md`
- Project status and evidence map: `docs/PROJECT_STATUS.md`
- Simulator plan router: `docs/all_dps_nd_simulator_plan.md`

Main executables:

```text
releases/windows/xiv_shell_tts.exe
releases/windows/ffxiv_personal_ndps.exe
releases/windows/ffxiv_personal_ndps_modern/ffxiv_personal_ndps_modern.exe
```

Tracked executables are release snapshots. The current development authority is `src/` plus `docs/PROJECT_STATUS.md`; rebuild the executables when publishing a new binary release.

`xiv_shell_tts.exe` converts XIV in the Shell CSV exports into the old `TTS.py` txt format. It can also take an optional fight timeline txt and produce the old `MERGE.PY`-style merged timeline output.

`ffxiv_personal_ndps.exe` opens the personal nDPS simulator GUI. It also supports `--self-test`, which verifies packaged resources, 13 DPS smoke CSVs, historical target-data samples, the formula layer, and the bundled `ama_xiv_combat_sim` dependency.

After a simulation, both stable and modern UIs can re-slice the completed run into an arbitrary `[start, end)` time window. The window report reuses recorded hit rolls, attributes every skill/DoT/auto-attack by actual damage time, restores the phase-start resource snapshot, and does not run the simulation again.

Folder layout:

- `apps/ndps-ui/`: React/Vite/Electron modern UI.
- `src/`: simulator and converter source packages.
- `scripts/`: reproducible build, comparison, audit, and bridge scripts.
- `data/`: FF14 Chinese-English skill mapping files used by the converter.
- `examples/skill_lines/`: saved xivintheshell exports, converted CSVs, target sidecars, TTS skill lines, and merged timeline outputs.
- `results/calibration/`: canonical calibration and comparison evidence.
- `releases/windows/`: user-facing portable executables and short usage notes.
- `docs/`: active manual/status docs plus archived historical reports.
- `artifacts/specs/`: the only tracked `artifacts/` surface; local build, cache, reference, and staging contents are ignored.

Rebuild command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_xiv_shell_tts_exe.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_ffxiv_ndps_simulator_exe.ps1
```

Simulator source entrypoint:

```powershell
.\.venv\Scripts\python.exe .\src\ffxiv_ndps_simulator\sim.py
```

Modern UI track:

```powershell
cd .\apps\ndps-ui
npm install
npm run dev
npm run desktop
```

The modern UI is a React/Vite dashboard plus Electron desktop shell. It keeps the validated simulator core in Python and uses `scripts/run_ndps_simulation.py` as the JSON bridge for desktop `Run Simulation`.

`src\ffxiv_ndps_simulator\sim_test.py` is now only a compatibility launcher that forwards to the unified `sim.py` GUI. The simulator report can export a Markdown summary plus CSV detail files for combat log, skill aggregation, coverage, resource warnings, and metadata.
