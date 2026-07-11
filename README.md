# FFXIV Personal nDPS Simulator

This repository is a personal rotation nDPS simulator for Final Fantasy XIV.
It imports raid-planner / XIV in the Shell style rotation files and simulates a
single player's output with Patch 7.5 job mechanics, target counts, untargetable
windows, DoTs, pets, follow-up hits, auto attacks, and job resources.

For the full user manual, see [docs/USER_MANUAL.md](docs/USER_MANUAL.md).
For the current evidence boundary, see [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

## Download

Use the GitHub Releases page for normal downloads:

- Latest release: <https://github.com/YuukiErii/FFXIV-nDPS-Simulator/releases/latest>
- Recommended modern package: `ffxiv_personal_ndps_v2_windows.zip`

Important: the modern UI is not a true single-file executable. Do not download
only `ffxiv_personal_ndps_v2.exe` and move it elsewhere. It needs the Electron
runtime files, `resources\app`, and `resources\backend` that sit next to it.

Correct modern UI usage:

1. Download `ffxiv_personal_ndps_v2_windows.zip` from Releases.
2. Extract the whole zip to a folder.
3. Run `ffxiv_personal_ndps_v2.exe` inside the extracted folder.

If Windows shows an unknown-publisher warning, allow the app manually. If Windows
marks the zip as downloaded from the internet, unblock the zip or the extracted
exe from file properties before launching.

The repository also keeps the local Windows build outputs here:

```text
releases/windows/ffxiv_personal_ndps.exe
releases/windows/ffxiv_personal_ndps_modern/ffxiv_personal_ndps_v2.exe
```

The stable legacy executable `ffxiv_personal_ndps.exe` is a standalone PyInstaller
one-file build. The modern `ffxiv_personal_ndps_v2.exe` is the launcher inside a
portable folder package.

## Which version should I use?

### Modern UI: `ffxiv_personal_ndps_v2.exe`

This is the recommended daily UI.

Features:

- React / Vite / Electron desktop interface.
- Uses the same simulator core as the legacy app: `src/ffxiv_ndps_simulator/sim.py`.
- Imports rotation CSV files, optional target TXT/JSON files, and optional
  untargetable track TXT files.
- Supports post-run `[start, end)` window nDPS recalculation without rerolling
  random damage.
- Shows skill details, potency grouping, target count, buffs, guaranteed
  critical/direct-critical flags, average hit, combat log, DoT rows, warnings,
  and window summaries.
- Best for comparing skill counts, buff coverage, target counts, and window
  output against planner websites.

Basic workflow:

1. Extract the full modern package zip.
2. Run `ffxiv_personal_ndps_v2.exe`.
3. Select the job and Patch 7.5 profile.
4. Enter main stat, critical hit, determination, direct hit, skill/spell speed,
   weapon damage, and other gear stats.
5. Select the rotation CSV.
6. Optionally select a target TXT/JSON file and a `MarkerTrackIndividual`
   untargetable track TXT file.
7. Run the simulation and inspect the overview, skill table, combat log, DoT,
   resource warning, and window nDPS panels.

### Stable legacy UI: `ffxiv_personal_ndps.exe`

This is the older Tk GUI and the conservative regression surface.

Features:

- One-file Python GUI package.
- Supports `--self-test` for quick packaged-resource and sample validation.
- Stable Markdown / CSV report export.
- Useful as a fallback when checking whether a problem belongs to the modern UI
  shell or to the shared simulator core.

Run it with:

```powershell
.\releases\windows\ffxiv_personal_ndps.exe
```

Run the packaged self-test with:

```powershell
.\releases\windows\ffxiv_personal_ndps.exe --self-test
```

## Input files

Common input set:

- Rotation CSV: required. Usually exported from XIV in the Shell, raid-planner,
  or a compatible planner.
- Target TXT/JSON: optional. Keeps target count, target swaps, and multi-target
  metadata.
- Track TXT: optional. Converts untargetable / downtime markers into global
  downtime windows.

CSV files should at least contain time and skill name fields. Extra fields such
as `castTime`, `positionalHit`, or target metadata make the simulation closer to
the original rotation. Positionals default to hit; set `positionalHit=false`
explicitly if you want to model missed positionals.

Track TXT files recognize marker descriptions containing `untargetable`, `上天`,
or `不可选中`, and convert `time` to `time + duration` into downtime.

## Simulation scope

Currently modeled:

- Player direct damage, DoTs, and auto attacks.
- Pets, summons, shadow/echo/follow-up hits, delayed resolution, and channel ticks.
- Personal buffs, job resources, combo state, proc-ready actions when present in
  the rotation, cast snapshots, and multi-target falloff.
- Untargetable windows and the resulting hit / DoT attribution.
- Post-run window re-aggregation from already generated damage events.

Not currently modeled:

- Strict FFLogs-equivalent rDPS with full party-buff contribution accounting.
  External party timelines and teammate contribution attribution are future Task M.
- Hidden proc reconstruction from logs. If a proc action appears in the rotation, the
  simulator treats it as already available.
- Automatic correction of invalid planner rotations. Resource warnings are surfaced
  but do not block simulation.

So the tool is best used for personal-rotation comparison, skill-count checking,
buff coverage, window output, and mechanics modeling. Final log-grade claims
still need real logs, AMAS output, or equivalent external audit.

## Current job evidence boundary

"Stable" here means no known simulator-mechanics issue under this repository's
current evidence boundary. It does not mean official FFLogs certification.

Confirmed stable jobs:

| Job | Current status |
| --- | --- |
| SAM | Mechanic and sample checks completed; default positionals hit; Meditation, Kenki, Tsubame, Ogi, and related paths have no known issue. |
| RPR | Mechanic checks completed; Arcane Circle / Immortal Sacrifice defaults to 8 stacks; Enshroud, Lemure/Void chains, Gluttony, Harvest, and raid-buff paths have no known issue. |
| RDM | Mechanic checks completed; Embolden affects self magical damage only and does not buff physical skills such as Fleche, Contre Sixte, Engagement, Corps-a-corps, Displacement, or enchanted melee hits. Cast, Dualcast, Swiftcast, and Acceleration behavior has been checked. |
| PCT | Mechanic checks completed; Starry Muse, motifs, muses, hammer combo, Comet in Black, multi-target falloff, guaranteed direct-critical display, and cast snapshot timing have been checked. |
| BLM | Mechanic checks completed; Patch 7.5 Astral Fire / Umbral Ice no longer expire; multi-target, dual-target DoT behavior, spell-speed casts, and slidecast snapshot timing have been checked. |

Jobs that are implemented but should still be treated cautiously until more
real-log or externally audited samples are checked:

| Job | Current caution |
| --- | --- |
| NIN | Patch 7.5 official mechanics checked and the retained M12S-P2 NIN 830 rotation was calibrated. Real-log validation is still recommended for Dokumori, Kunai's Bane, Bunshin, Ninki windows, and final numerical boundaries. |
| MNK | Official mechanics checked; teammate Chakra is averaged at one stack per 0.4s and Brotherhood raises Chakra cap to 10. Hidden random Chakra / proc details still benefit from real samples. |
| DRG | Official mechanics checked; Power Surge and Life of the Dragon double-count protection is in place. Real long-rotation samples should continue checking jump follow-ups, Life windows, and auto attacks. |
| VPR | Official mechanics checked; combo chains, venoms, Reawaken, Generation / Legacy / Ouroboros, Hunter's Instinct, Swiftscaled, and falloff are modeled. Fixed axes do not auto-rearrange GCDs from haste. |
| BRD | Official mechanics checked; Army's Muse / Ethos carryover is modeled. Repertoire and proc actions are treated as available when already present in the rotations. |
| MCH | Official mechanics checked; Wildfire, Hypercharge, Reassemble, Full Metal Field, Flamethrower, Queen, and battery scaling are modeled. Some external exports still have Heat Blast / Queen attribution boundaries. |
| DNC | Official mechanics checked; Technical Finish defaults to four steps, Enhanced Esprit self GCD gains are modeled, and proc actions in the rotations are treated as already triggered. Dance partner contribution remains future Task M scope. |
| SMN | Official mechanics checked; summons use the calibrated effective 0.8 pet coefficient. More valid real-log samples are recommended for final summon timeline validation. |

These eight jobs are not known-broken; their evidence level is simply lower than
the five jobs above.

## Development

Create the Python environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Run the source GUI:

```powershell
.\.venv\Scripts\python.exe .\src\ffxiv_ndps_simulator\sim.py
```

Run the modern UI in development:

```powershell
cd .\apps\ndps-ui
npm install
npm run dev
npm run desktop
```

Rebuild release outputs:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_ffxiv_ndps_simulator_exe.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_modern_ndps_ui.ps1
```

Common validation commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\smoke_damage_formula.py
.\.venv\Scripts\python.exe scripts\scan_skill_coverage.py examples\skill_lines --issues-only --show-skills
.\releases\windows\ffxiv_personal_ndps.exe --self-test
npm --prefix apps\ndps-ui run build
npm --prefix apps\ndps-ui run smoke:desktop
npm --prefix apps\ndps-ui run smoke:packaged
```

## Repository layout

- `src/ffxiv_ndps_simulator/`: simulator core.
- `apps/ndps-ui/`: modern React / Electron UI.
- `scripts/`: packaging, bridge, calibration, and scan scripts.
- `examples/skill_lines/`: sample axes, target sidecars, track files, and
  converted skill-line files.
- `results/calibration/`: calibration and comparison evidence.
- `releases/windows/`: local Windows release outputs.
- `docs/`: user manual, project status, and historical archive.
