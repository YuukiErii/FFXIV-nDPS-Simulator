# FFXIV Personal nDPS Simulator

Full workspace manual: `..\..\docs\USER_MANUAL.md`

## Files

- `ffxiv_personal_ndps.exe`: packaged simulator GUI and command-line self-test.
- `ffxiv_personal_ndps_readme.md`: this release note.

## Quick Check

Run:

```powershell
.\ffxiv_personal_ndps.exe --self-test
```

The self-test validates bundled resources, `ama_xiv_combat_sim` skill data, the formula smoke check, all 13 DPS job CSV smoke samples, and 4 historical target-data samples. It returns a non-zero exit code if any check fails.

## GUI Usage

Double-click `ffxiv_personal_ndps.exe` to open the GUI. A console window may appear because the release keeps command-line self-test output visible.

1. Choose the job.
2. Import a timeline CSV exported from xivintheshell / the raid planner.
3. Optionally import a matching JSON/TXT target file to preserve multi-target counts.
4. Run the simulation and export Markdown or CSV evidence bundles when needed.

## Inputs

- Required: timeline CSV with `time` and `action` columns, or a compatible positional/TTS skillline CSV.
- Optional: matching `.json` or `.txt` target data with `actions`, `skillName`, and either `targetList` or `targetCount`.

## nDPS Boundary

This MVP reports personal nDPS/RD for damage attributed to the selected job: skills, DoTs, auto-attacks, pets/summons/follow-ups, and self buffs. It does not subtract external party-buff gain and does not distribute party-buff contribution to teammates.

## Known Limits

- Smoke samples prove import, resource paths, state-machine reachability, and positive simulated damage; they are not FFLogs-equivalent numerical validation.
- Some long-axis comparisons are xivintheshell regression baselines rather than real-log calibration.
- Resource warnings are shown in reports and exports; warning-only samples can still be useful for debugging timing or legality assumptions.

## Rebuild

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_ffxiv_ndps_simulator_exe.ps1
```
