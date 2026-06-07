# FFXIV SIM Project Status

Updated: 2026-06-08

This document is the active development status and evidence map for the FFXIV SIM workspace. It consolidates the former roadmap, calibration matrix, Task I audit pointer, SAM regression audit pointer, filename migration notes, and the original Chinese user-facing draft into one readable control surface.

## Active Document Map

- User manual: `docs/USER_MANUAL.md`
- Plan router: `docs/all_dps_nd_simulator_plan.md`
- Current project status: `docs/PROJECT_STATUS.md`
- Historical and generated reports: `docs/archive/`

The original long implementation plan is archived at `docs/archive/all_dps_nd_simulator_plan_2026_05_28.md`. Keep `docs/all_dps_nd_simulator_plan.md` in place because local workflows and continuation agents use that path as the first routing artifact.

## Product Surfaces

| Surface | Path | Status | Notes |
| --- | --- | --- | --- |
| Stable simulator GUI | `releases/windows/ffxiv_personal_ndps.exe` | Released MVP | Packaged Python GUI and `--self-test` remain the stable user surface. |
| Source simulator | `src/ffxiv_ndps_simulator/sim.py` | Maintained source of truth | `sim_test.py` is only a compatibility launcher. |
| Modern UI | `apps/ndps-ui` | Packaged desktop track | React/Vite/Electron shell calls `scripts/run_ndps_simulation.py` through the desktop bridge. |
| XIVShellTTS converter | `releases/windows/xiv_shell_tts.exe` | Released helper tool | Converts XIV in the Shell CSV exports to old TTS-style skill-line text and optional merged timeline output. |

## Current Simulator State

- Phase 0 to Phase 3 are complete: baseline preservation, CSV import, formula module, simulator core split, coverage reporting, and report/export surfaces are in place.
- Phase 4 MVP is complete for all 13 DPS jobs: SAM, MNK, DRG, NIN, RPR, VPR, BRD, MCH, DNC, BLM, SMN, RDM, and PCT all have job-state support at the current "axis can be interpreted" level.
- Task I is closed for the current plan scope: reproducible xivintheshell per-skill comparisons exist for MNK, DRG, VPR, BRD, MCH, DNC, SMN, and RDM, with remaining differences recorded as evidence boundaries.
- Task J is closed for the current plan scope: all 13 DPS job state classes support warning-only resource legality ledgers that do not block simulation.
- Task K is closed: the maintained GUI entrypoint, report header, evidence levels, Markdown export, CSV detail export, and resource-warning surfacing are wired.
- Task L is closed: source self-test, packaged simulator self-test, release packaging, and GitHub sync have been completed in prior release commits.
- Task M remains future work: external party-buff timelines, teammate contribution accounting, and FFLogs-like strict nDPS are not part of the current MVP.

## Evidence Levels

Use these terms conservatively in code, docs, and reports:

| Level | Meaning |
| --- | --- |
| `import_smoke_passed` | The axis parses, coverage has no blocking unknowns, and the simulator produces positive damage. |
| `xivintheshell_damage_compared` | A matching xivintheshell damage export and reproducible per-skill comparison table exist. Stronger than import smoke, but not real-log validation. |
| `mechanic_calibrated` | Skill counts, target counts, combo/replacement behavior, DoT ticks, pet/follow-up events, and special mechanics have been compared enough to explain remaining differences. |
| `log_validated` | Per-skill output has been compared against an actual combat log, AMAS output, or an externally audited equivalent. No job should be described as log validated without that evidence. |

## Job Evidence Matrix

| Job | Best current sample | Current evidence | Next calibration focus |
| --- | --- | --- | --- |
| SAM | `examples/skill_lines/sam_m9_m12s/m11s_217.csv` | Historical long-axis import smoke | Restore/guard backup-authoritative SAM replay parity before claiming numerical stability. |
| NIN | `examples/skill_lines/nin_m12s_p2/nin_830.csv` | Historical long-axis import smoke | Compare mudra, Bunshin, Dokumori, and resource timing against external totals. |
| RPR | `examples/skill_lines/rpr_enuo/reaper.csv` | Historical long-axis import smoke | Compare Enshroud, Lemure/Void chains, Communio, Plentiful Harvest, and target attribution. |
| PCT | `examples/skill_lines/pct_fru/23_desaturation.csv` | Historical FRU long-axis import smoke | Compare motif, muse, hammer, comet, creature follow-ups, and multi-target phases. |
| BLM | `examples/skill_lines/sam_m9_m12s/sam_misc/suiyue_jiyu_9s.csv` | Historical long-axis import smoke | Move or alias BLM-owned samples, then compare Astral/Umbral state, Thunder ticks, and target counts. |
| MNK | `examples/skill_lines/mnk_xivintheshell_long/mnk_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit Blitz/Fire's Reply attribution and auto-attack count drift with stronger evidence. |
| DRG | `examples/skill_lines/drg_xivintheshell_long/drg_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit Life of the Dragon, jump follow-ups, Wyrmwind, and Chaotic Spring. |
| VPR | `examples/skill_lines/vpr_xivintheshell_long/vpr_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit Generation/Legacy chains, Reawaken, and Serpent Offering flow. |
| BRD | `examples/skill_lines/brd_xivintheshell_long/brd_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit song state, Repertoire, DoT snapshot/Iron Jaws, and Radiant Finale timing. |
| MCH | `examples/skill_lines/mch_xivintheshell_long/mch_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Keep Heat Blast marked as xivintheshell export gap until a positive-potency export exists. |
| DNC | `examples/skill_lines/dnc_xivintheshell_long/dnc_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit dance resolution, Esprit, Flourish replacements, and dance-partner boundary. |
| SMN | `examples/skill_lines/smn_xivintheshell_long/smn_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Replace or support the mechanically loose manual axis; warning rows identify suspect summon/gem segments. |
| RDM | `examples/skill_lines/rdm_xivintheshell_long/rdm_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit melee-combo mana spend, Verflare/Verholy chain, Embolden timing, and auto-attack windows. |

## Current Evidence Artifacts

- Canonical calibration output directory: `results/calibration/`
- Task I generated audit: `docs/archive/task_i_xivintheshell_comparison_audit.md`
- SAM backup/stable regression audit: `docs/archive/sam_backup_stable_rd_regression_audit_2026_05_31.md`
- Filename migration record: `docs/archive/filename_migration_2026_05_28.md`

The old duplicate `artifacts/calibration/` surface is retired. Build specs and local build/cache material remain under `artifacts/`.

## Regression Commands

Run the checks that match the layer touched. For documentation-only edits, markdown/path checks and `git diff --check` are usually enough.

```powershell
.\.venv\Scripts\python.exe scripts\scan_skill_coverage.py examples/skill_lines --issues-only --show-skills
.\.venv\Scripts\python.exe scripts\compare_xivintheshell_damage.py
.\.venv\Scripts\python.exe scripts\audit_xivintheshell_comparisons.py
.\.venv\Scripts\python.exe scripts\smoke_damage_formula.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\releases\windows\ffxiv_personal_ndps.exe --self-test
```

## Folder Policy

- `docs/` keeps only active reading surfaces plus `docs/archive/` for historical reports.
- `results/` is the canonical place for calibration and reproducible result evidence.
- `artifacts/` is for specs, local build output, cache, reference checkouts, duplicates, and other non-primary generated material.
- `examples/skill_lines/` stores sample axes, target sidecars, translated CSVs, and skill-line or merged timeline files.
- `releases/windows/` stores user-facing binaries and short release notes.

## Archive Index

| Archived document | Purpose |
| --- | --- |
| `docs/archive/all_dps_nd_simulator_plan_2026_05_28.md` | Original long Chinese implementation plan and task history. |
| `docs/archive/simulator_calibration_matrix_2026_05_28.md` | Former per-job calibration matrix, now summarized here. |
| `docs/archive/task_i_xivintheshell_comparison_audit.md` | Generated Task I triage report from comparison CSVs. |
| `docs/archive/sam_backup_stable_rd_regression_audit_2026_05_31.md` | SAM backup versus maintained-core regression audit. |
| `docs/archive/filename_migration_2026_05_28.md` | Old-to-new path mapping from the repository reorganization. |
| `docs/archive/original_user_note_cn_2026_01_31.md` | Original Chinese draft explaining the tool idea and user workflow. |
