# FFXIV SIM Project Status

Updated: 2026-07-02

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
- Task I is closed for the current plan scope: reproducible xivintheshell per-skill comparisons exist for NIN, MNK, DRG, VPR, BRD, MCH, DNC, SMN, and RDM, with remaining differences recorded as evidence boundaries.
- Task J is closed for the current plan scope: all 13 DPS job state classes support warning-only resource legality ledgers that do not block simulation.
- Task K is closed: the maintained GUI entrypoint, report header, evidence levels, Markdown export, CSV detail export, and resource-warning surfacing are wired.
- Task L is closed: source self-test, packaged simulator self-test, release packaging, and GitHub sync have been completed in prior release commits.
- Task M remains future work: external party-buff timelines, teammate contribution accounting, and FFLogs-like strict nDPS are not part of the current MVP.
- 2026-06-30 all-job regression gate passed for the current framework: 113 unit tests, skill coverage scan, xivintheshell comparison/audit regeneration, damage-formula smoke, and `git diff --check` completed without blocking errors. Remaining comparison rows are documented sample/export/timing boundaries rather than unmodeled skill-coverage gaps.
- 2026-06-30 repository hygiene pass moved BLM-owned M10S samples out of the SAM archive, retired reproducible test outputs and unreferenced performance dumps, and made `artifacts/specs/` the only tracked `artifacts/` surface.
- 2026-06-30 stable and modern Windows packages were rebuilt from the current source. The stable EXE passed its packaged 13-job self-test; the modern package passed packaged-backend simulation and Electron launch smoke checks.
- 2026-07-01 raid-planner `MarkerTrackIndividual` untargetable TXT files can be imported as global downtime through a dedicated modern UI Track TXT slot, so target metadata and untargetable windows can be submitted together. Source tests, SAM DMU import scan, stable packaged self-test, and packaged modern backend marker-track smoke checks passed.
- 2026-07-01 stable GUI now also has separate target TXT and untargetable-track TXT inputs; reports and metadata list target-source and downtime-source separately.
- 2026-07-01 modern UI report parity pass added stable-report surfaces to the packaged desktop track: evidence, inputs, panel stats, result extrema, warnings, skill DPS, best run, interval RD, distribution, coverage, and combat log are visible after a run.
- 2026-07-01 modern UI structure now mirrors the stable GUI's nine report columns. Stable table fields, totals, distribution axes/curve/percentile markers, and normalized import preview are retained while the desktop shell uses the warm-black, teal, and gold visual palette with a bundled Claude-theme font stack.
- 2026-07-01 modern UI typography now follows the complete Claude font-role split: Serif for report prose, Sans for interface labels, and Mono for numeric/code-like data, each with its intended Chinese fallback. The interface and default desktop window were enlarged while preserving the nine-column report content.
- 2026-07-02 stable and modern UIs added post-run `[start, end)` time-window nDPS reports. The completed simulation now retains compact per-run damage events plus a first-run resource timeline; changing the window re-aggregates actual hit-time damage, phase-start resources, skill/DoT/auto-attack rows, extrema, warnings, and distributions without running the simulator again. The 130-test suite, stable packaged self-test/launch, modern packaged backend simulation-to-window smoke, and Electron launch smoke passed before release refresh.

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
| NIN | `examples/skill_lines/nin_m12s_p2/nin_830.csv` | `mechanic_calibrated` | Seek real-log or independently audited numerical validation; the retained axis still has two intentional Ninki-overcap warnings. |
| RPR | `examples/skill_lines/rpr_enuo/reaper.csv` | Historical long-axis import smoke | Compare Enshroud, Lemure/Void chains, Communio, Plentiful Harvest, and target attribution. |
| PCT | `examples/skill_lines/pct_fru/23_desaturation.csv` | Historical FRU long-axis import smoke | Compare motif, muse, hammer, comet, creature follow-ups, and multi-target phases. |
| BLM | `examples/skill_lines/blm_m10s/m10s_1b3.csv` | Historical long-axis import smoke | Compare Astral/Umbral state, Thunder ticks, cast timing, and target counts against an external damage export. |
| MNK | `examples/skill_lines/mnk_xivintheshell_long/mnk_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Form/Fury, Chakra, Perfect Balance/Beast Chakra/Nadi/Blitz, replies, and auto-attack haste are modeled; auto attacks now match 94/94. The retained manual axis still contains one expired Fire's Reply and one unready Masterful Blitz, both warning-only. |
| DRG | `examples/skill_lines/drg_xivintheshell_long/drg_xivintheshell_long.csv` | `xivintheshell_damage_compared` | Revisit Life of the Dragon, jump follow-ups, Wyrmwind, and Chaotic Spring. |
| VPR | `examples/skill_lines/vpr_xivintheshell_long/vpr_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Honed/venom potency, single-target and AoE combos, all three dualblade follow-up chains, Rattling Coil, Serpent Offering, Reawaken/Generation/Legacy/Ouroboros, Hunter's Instinct, Swiftscaled, positionals, and 7.5 falloff are modeled; seek real-log numerical validation next. |
| BRD | `examples/skill_lines/brd_xivintheshell_long/brd_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Songs and song buffs, Coda/Radiant Finale/Radiant Encore, Repertoire/Pitch Perfect, Barrage/Refulgent/Shadowbite, Soul Voice/Apex/Blast Arrow, Resonant Arrow, Army's Paeon haste, double DoT snapshotting, and Iron Jaws refresh behavior are modeled. Trigger/resource actions present in the axis are treated as already ready where the CSV lacks the hidden proc/resource detail. The retained long axis still has three expired-Iron-Jaws warnings plus Apex/Radiant Encore and auto-attack count boundaries from the external export. |
| MCH | `examples/skill_lines/mch_xivintheshell_long/mch_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Heat/Battery generation, Reassemble allowlist, Hypercharged, 5-stack Overheated with +20 single-target weaponskill potency, Barrel Stabilizer's Hypercharged + Full Metal Machinist grants, Excavator Ready, Full Metal Field CDH behavior, Wildfire counting with Detonator early resolution, Flamethrower's channeled physical-DoT ticks/cancel boundary, and Battery-scaled Queen follow-ups including Roller Dash are modeled. Retained xivintheshell comparison still marks Heat Blast/Roller Dash export-attribution gaps, one official-Detonator Wildfire count boundary in the retained axis, and auto-attack count drift. |
| DNC | `examples/skill_lines/dnc_xivintheshell_long/dnc_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Standard/Technical Finish potency and buff scaling, default full four-step Technical Finish, Devilment/Starfall, Flourish/Finishing Move/Fan Dance ready handling, Last Dance, Tillana +50 Esprit, Dance of the Dawn/Saber Dance spend behavior, self Esprit gain under dance buffs, and trigger skills present in an axis as already-ready actions are modeled. Retained xivintheshell comparison still has Finishing Move export attribution, Fan Dance/Last Dance/Starfall count deltas, and one auto-attack timing boundary; teammate dance-partner contribution remains Task M scope. |
| SMN | `examples/skill_lines/smn_xivintheshell_long/smn_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Demi cycle/actions/autos, elemental arcanum/attunement/favors, Aetherflow/Further Ruin, Searing Flash/Refulgent Lux, pet application timing, AoE falloff, snapshots, and the effective 0.8 pet coefficient are modeled. The retained manual axis has 15 warning-only invalid summon/gem rows; seek a mechanically valid real-log axis for final numerical validation. |
| RDM | `examples/skill_lines/rdm_xivintheshell_long/rdm_xivintheshell_long.csv` | `official_7_5_mechanics_checked`; `xivintheshell_damage_compared` | Dualcast/Swiftcast/Acceleration cast overrides, exact black/white mana gains and costs, Mana Stack finishers, 7.5 Manafication/Magicked Swordplay, Thorned Flourish, Prefulgence Ready, Embolden, and retained caster auto-attack cadence are modeled; seek real-log numerical validation next. |

## Current Evidence Artifacts

- Canonical calibration output directory: `results/calibration/`
- Task I generated audit: `docs/archive/task_i_xivintheshell_comparison_audit.md`
- SAM backup/stable regression audit: `docs/archive/sam_backup_stable_rd_regression_audit_2026_05_31.md`
- NIN mechanic and accuracy audit: `docs/archive/nin_nd_accuracy_audit_2026_06_29.md`
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
- `results/calibration/` is the canonical tracked result surface. Reproducible test output belongs in ignored `results/test_outputs/`.
- `artifacts/specs/` is tracked; every other `artifacts/` child is local build, cache, reference, staging, or scratch material and is ignored.
- `examples/skill_lines/` stores sample axes, target sidecars, translated CSVs, and skill-line or merged timeline files.
- `releases/windows/` stores user-facing binaries and short release notes.

## Archive Index

| Archived document | Purpose |
| --- | --- |
| `docs/archive/all_dps_nd_simulator_plan_2026_05_28.md` | Original long Chinese implementation plan and task history. |
| `docs/archive/simulator_calibration_matrix_2026_05_28.md` | Former per-job calibration matrix, now summarized here. |
| `docs/archive/task_i_xivintheshell_comparison_audit.md` | Generated Task I triage report from comparison CSVs. |
| `docs/archive/sam_backup_stable_rd_regression_audit_2026_05_31.md` | SAM backup versus maintained-core regression audit. |
| `docs/archive/nin_nd_accuracy_audit_2026_06_29.md` | NIN skill coverage, output mechanics, closed accuracy gaps, and external comparison boundary. |
| `docs/archive/filename_migration_2026_05_28.md` | Old-to-new path mapping from the repository reorganization. |
| `docs/archive/original_user_note_cn_2026_01_31.md` | Original Chinese draft explaining the tool idea and user workflow. |
