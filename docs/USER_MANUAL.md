# FFXIV SIM User Manual

This manual is the unified entry point for the tools in this repository. It covers the packaged Windows executables, the simulator source GUI, the modern nDPS desktop UI, and the XIV in the Shell to TTS converter.

## Tool Overview

Use `releases\windows\ffxiv_personal_ndps.exe` for the stable packaged personal nDPS simulator. It opens a GUI, imports an axis CSV, can attach target metadata, runs the simulator, and exports Markdown or CSV evidence.

Use `apps\ndps-ui` for the newer high-ceiling UI track. It is a React/Vite dashboard with an Electron desktop shell. It keeps the validated simulator core in Python and calls it through `scripts\run_ndps_simulation.py`.

Use `releases\windows\xiv_shell_tts.exe` to convert XIV in the Shell CSV exports into old `TTS.py`-style skill-line text, optionally merged with a fight timeline.

Use `src\ffxiv_ndps_simulator\sim.py` when developing or running the simulator directly from Python.

## Recommended Entry Points

Stable simulator GUI:

```powershell
.\releases\windows\ffxiv_personal_ndps.exe
```

Packaged simulator verification:

```powershell
.\releases\windows\ffxiv_personal_ndps.exe --self-test
```

Modern UI development or desktop preview:

```powershell
cd .\apps\ndps-ui
npm install
npm run dev
npm run desktop
```

Source simulator GUI:

```powershell
.\.venv\Scripts\python.exe .\src\ffxiv_ndps_simulator\sim.py
```

TTS conversion:

```powershell
.\releases\windows\xiv_shell_tts.exe
```

## Personal nDPS Simulator Workflow

1. Open `ffxiv_personal_ndps.exe` or run `sim.py` from source.
2. Choose the job that matches the imported axis.
3. Fill the stat fields. The simulator uses these values for damage formula calculation.
4. Import an axis CSV exported from XIV in the Shell or a compatible raid planner.
5. Optionally import a matching target JSON or TXT file. This preserves multi-target counts when the axis itself does not contain enough target metadata.
6. Configure DoT target rules, downtime, multi-boss behavior, and report thresholds if the fight needs them.
7. Run the simulation.
8. Read the result tab, coverage summary, target-source status, and resource warnings.
9. Export a Markdown report or CSV detail bundle when you need a durable record.

The simulator report can export:

- Markdown summary
- combat log CSV
- skill aggregation CSV
- coverage CSV
- resource warning CSV
- metadata CSV

## Modern nDPS UI Workflow

The modern UI has two modes.

In browser mode, `npm run dev` starts the Vite app. You can import local files through the browser file picker, inspect the dashboard, and export a UI snapshot JSON.

In desktop mode, `npm run desktop` builds the UI and opens Electron. Electron keeps native file paths, so `Run Simulation` can call:

```powershell
.\scripts\run_ndps_simulation.py
```

The desktop bridge sends the selected axis path, optional target path, selected job, stat fields, and simulation options to Python, then renders the returned summary, timeline, coverage, and warnings.

Current boundary: the modern UI is the preferred visual direction, but the packaged `ffxiv_personal_ndps.exe` remains the stable release surface. Treat the modern UI as the polished desktop track while the Python simulator remains the source of calculation truth.

## XIVShellTTS Workflow

Use the GUI when you only need conversion:

1. Open `xiv_shell_tts.exe`.
2. Choose an exported XIV in the Shell CSV.
3. Convert to a TTS skill-line text file.
4. Optionally choose a fight timeline text file. The converter will also write a merged timeline output.

Drag-and-drop is also supported. Dropping a CSV onto the executable writes:

- `<input>_skillline.txt`
- `<input>CN.csv`

CLI example:

```powershell
.\releases\windows\xiv_shell_tts.exe --convert .\axis.csv --out .\axis_skillline.txt --cn-csv .\axis_cn.csv --timeline .\fight_timeline.txt --merged-out .\axis_merged.txt
```

The converter uses `data\ff14_job_skill_en_cn_map.json`. Untranslated action names are preserved instead of being dropped.

## Input Formats

Axis CSV input should contain at least:

- `time`
- `action`

Optional columns such as `isGCD`, `castTime`, and target-related metadata improve preview and simulation fidelity when available.

The simulator can also parse compatible positional or TTS skill-line CSV files. When possible, prefer the original raid-planner axis CSV because it usually keeps more timing and target metadata.

Target JSON or TXT files should contain action records. Useful fields include:

- `actions`
- `type: Skill`
- `skillName`
- `targetList`
- `targetCount`

When no target metadata is available, simulator rows default to target count `1`. The report labels this as default target data so the result can be interpreted correctly.

Timeline text files for TTS merging may contain an optional leading `#` and a numeric timestamp. Merge output reads the fight timeline first, then the skill-line text, parses the first numeric timestamp on each non-empty line, and stable-sorts all parsed lines by timestamp.

## Outputs

Simulator outputs are produced from the GUI export actions. Recommended locations are under `results\` or a run-specific folder outside source directories.

TTS converter outputs are usually written next to the input CSV:

- translated Chinese CSV
- TTS skill-line text
- optional merged timeline text

Modern UI snapshot export writes `ndps-ui-snapshot.json` from the browser. Desktop simulation results are displayed in the UI and are produced by the Python JSON bridge.

## Evidence Boundaries

Personal nDPS here means damage attributed to the selected player/job: direct skills, DoTs, auto-attacks, pets, summons, follow-ups, and self buffs where modeled. It does not subtract external party-buff gain and does not distribute party-buff contribution to teammates.

Self-tests and smoke samples validate import behavior, resource paths, parser coverage, state-machine reachability, positive simulated damage, and regression stability. They are not FFLogs-equivalent numerical validation.

Some long-axis comparisons are regression baselines from xivintheshell-style inputs rather than real-log calibration.

Resource warnings are warning-only. A run with warnings can still be useful for trend checks or debugging, but it should not be treated as a clean legality-validated result without review.

## Folder Layout

`apps\` contains frontend and desktop app workspaces. `apps\ndps-ui` is the modern React/Vite/Electron nDPS UI.

`src\` contains Python source packages. `src\ffxiv_ndps_simulator` is the simulator; `src\xiv_shell_tts` is the TTS converter.

`scripts\` contains reproducible build, conversion, and bridge scripts.

`data\` contains generated or curated data used by the tools, including the FF14 English-Chinese skill map.

`examples\skill_lines\` contains sample raid-planner exports, translated CSVs, TTS skill lines, and merged outputs.

`results\` is the canonical place for calibration and result artifacts that should remain separate from source.

`releases\windows\` contains user-facing portable Windows executables and short release notes.

`docs\` contains this manual, `PROJECT_STATUS.md`, the lightweight plan router, and archived historical notes under `docs\archive\`.

`artifacts\` is for build specs and local generated artifacts. Build caches, reference checkouts, old duplicate calibration outputs, duplicates, and legacy binary staging are ignored by Git.

`archive\` contains preserved older material.

`tests\` contains automated checks.

## Rebuild Commands

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_xiv_shell_tts_exe.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_ffxiv_ndps_simulator_exe.ps1
```

Modern UI build:

```powershell
cd .\apps\ndps-ui
npm run build
```

Modern UI Windows package:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_modern_ndps_ui.ps1
```

The packaged modern UI is written to `releases\windows\ffxiv_personal_ndps_modern\` and includes a bundled Python JSON backend at `resources\backend\ndps_backend.exe`.

## Troubleshooting

Run the simulator self-test first when a packaged executable behaves unexpectedly:

```powershell
.\releases\windows\ffxiv_personal_ndps.exe --self-test
```

If a CSV fails to parse, confirm that it has `time` and `action` columns, or use the original raid-planner export rather than a post-processed TTS file.

If target counts look too low, import the matching JSON or TXT target file. Without target metadata, the simulator intentionally falls back to target count `1`.

If resource warnings appear, inspect the warning rows in the report or exported CSV. Warnings usually mean the axis asks for a skill before the modeled resource state is ready, or a timing assumption needs review.

If `npm install` fails while downloading Electron, retry with a reachable Electron mirror:

```powershell
$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
npm install
```

If Node or npm is not available in a clean Windows shell, install a current Node.js LTS runtime or run from the Codex workspace runtime used by this repository.

## Development Hygiene

Do not commit local dependency folders or build caches:

- `node_modules\`
- `apps\*\node_modules\`
- `apps\*\dist\`
- `artifacts\cache\`
- `artifacts\build\`

Keep sample axes under `examples\skill_lines\`, result evidence under `results\`, user-facing binaries under `releases\windows\`, and source changes under `src\`, `apps\`, or `scripts`.

When changing simulator behavior, keep the Python core as the source of truth and use the modern UI bridge only as a presentation and orchestration layer.

For current development status, evidence levels, and the archive index, read `docs\PROJECT_STATUS.md`.
