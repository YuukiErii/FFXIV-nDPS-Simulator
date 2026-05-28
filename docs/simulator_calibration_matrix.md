# Simulator Calibration Matrix

Last updated: 2026-05-28

This matrix tracks the current evidence level for each DPS job. It is intentionally conservative: a CSV that imports and simulates successfully is not treated as numerical validation until it has an external skill-level comparison.

## Status Levels

- `import_smoke_passed`: the CSV parses, `scan_skill_coverage.py` reports no unknown / needs_state / follow-up issues, and the simulator produces positive total damage.
- `mechanic_calibrated`: skill counts, target counts, combo / replacement behavior, DoT ticks, pet / follow-up events, and special job mechanics have been compared against an external xivintheshell closely enough to explain remaining differences.
- `log_validated`: the simulated per-skill output has been compared against an actual combat log, AMAS result, or an externally audited equivalent fight-axis damage xivintheshell.

Evidence tags used below:

- `xivintheshell_damage_compared`: a matching xivintheshell damage export exists and a reproducible per-skill comparison table has been generated. This is stronger than action import smoke, but it is not FFLogs / AMAS validation by itself.

Current summary:

- `examples/skill_lines` currently contains 88 CSV files: 80 action / axis candidates plus 8 xivintheshell damage-export CSVs.
- The coverage scanner treats `*_xivintheshell_damage.csv` as external-detail inputs and skips them during default directory scans.
- All 13 DPS jobs have at least one action / axis CSV that reaches `import_smoke_passed`.
- SAM / NIN / RPR / PCT / BLM have historical long-axis samples, but they still need a normalized external damage comparison before they can be marked `log_validated`.
- MNK / DRG / VPR / BRD / MCH / DNC / SMN / RDM now have manual xivintheshell long-axis candidates, matching xivintheshell damage exports, and per-skill comparison tables under `results/calibration`. These are stronger regression assets than short smoke openers, but still not FFLogs / AMAS numerical validation artifacts.
- Task J warning-only resource ledgers now exist for all 13 DPS job state classes. The compared long-axis jobs also emit `results/calibration/*_resource_warnings.csv` with `row_no`, time, skill, code, severity, and message.
- Repository organization, release packaging, and GitHub sync are complete as of commit `ccaabaf` on `main`; this does not change the evidence levels below, which remain intentionally conservative.

## Job Matrix

| Job | Best current sample | Sample type | Rows / unique skills | Target sidecar | Current level | External comparison | Next calibration task |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SAM | `examples/skill_lines/sam_m9_m12s/m11s_217.csv` | Historical long axis | 477 / 28 | TXT target lists in directory | `import_smoke_passed`; mechanics partially exercised | Not generated | Pick one representative M9-M12 axis, export or reconstruct per-skill external totals, then compare combo, Kaeshi, Ogi, DoT, target-count behavior. |
| NIN | `examples/skill_lines/nin_m12s_p2/nin_830.csv` | Historical long axis | 409 / 27 | `nin_830.txt` | `import_smoke_passed`; mechanics partially exercised | Not generated | Compare Mudra / Ninjutsu, Bunshin follow-ups, Dokumori window, and resource timing against xivintheshell or AMAS. |
| RPR | `examples/skill_lines/rpr_enuo/reaper.csv` | Historical long axis | 315 / 27 | `reaper.txt`; `timeline_enuo_trial.json` | `import_smoke_passed`; mechanics partially exercised | Not generated | Compare Enshroud windows, Lemure / Void Reaping chain, Communio, Plentiful Harvest, and target attribution. |
| PCT | `examples/skill_lines/pct_fru/23_desaturation.csv` | Historical FRU long axis | 442 / 34 | Multiple TXT target and timeline notes | `import_smoke_passed`; mechanics partially exercised | Not generated | Compare motif / muse / hammer / comet replacement handling, creature follow-ups, DoT or persistent effects, and multi-target phases. |
| BLM | `examples/skill_lines/sam_m9_m12s/sam_misc/suiyue_jiyu_9s.csv` | Historical long axis stored in SAM archive | 404 / 37 | Nearby TXT notes in `sam_misc` | `import_smoke_passed`; mechanics partially exercised | Not generated | Move or alias BLM samples into a BLM-owned directory, then compare Astral / Umbral state, Enochian, Thunder ticks, Foul / Xenoglossy, and target counts. |
| MNK | `examples/skill_lines/mnk_xivintheshell_long/mnk_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 64 / 19 | `mnk_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/mnk_xivintheshell_long/mnk_xivintheshell_damage.csv`; `results/calibration/mnk_xivintheshell_long_skill_comparison.csv` | Audit form / Riddle / Brotherhood / Blitz differences, then replace or supplement with AMAS / real-log evidence. |
| DRG | `examples/skill_lines/drg_xivintheshell_long/drg_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 57 / 20 | `drg_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/drg_xivintheshell_long/drg_xivintheshell_damage.csv`; `results/calibration/drg_xivintheshell_long_skill_comparison.csv` | Audit Life of the Dragon, Nastrond / Stardiver, jump follow-ups, and Chaotic Spring differences. |
| VPR | `examples/skill_lines/vpr_xivintheshell_long/vpr_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 81 / 28 | `vpr_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/vpr_xivintheshell_long/vpr_xivintheshell_damage.csv`; `results/calibration/vpr_xivintheshell_long_skill_comparison.csv` | Audit Generation / Legacy chains, Reawaken windows, combo replacements, and Serpent Offering flow. |
| BRD | `examples/skill_lines/brd_xivintheshell_long/brd_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 54 / 20 | `brd_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/brd_xivintheshell_long/brd_xivintheshell_damage.csv`; `results/calibration/brd_xivintheshell_long_skill_comparison.csv` | Audit song state, Repertoire, DoT snapshot / Iron Jaws, Radiant Finale, and party-buff timing. |
| MCH | `examples/skill_lines/mch_xivintheshell_long/mch_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 59 / 17 | `mch_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/mch_xivintheshell_long/mch_xivintheshell_damage.csv`; `results/calibration/mch_xivintheshell_long_skill_comparison.csv` | Audit Heat / Battery, Hypercharge, Wildfire hits, Automaton Queen, and follow-up timing. |
| DNC | `examples/skill_lines/dnc_xivintheshell_long/dnc_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 62 / 22 | `dnc_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/dnc_xivintheshell_long/dnc_xivintheshell_damage.csv`; `results/calibration/dnc_xivintheshell_long_skill_comparison.csv` | Audit dance step resolution, Esprit, Flourish replacements, Technical Finish, and dance-partner attribution. |
| SMN | `examples/skill_lines/smn_xivintheshell_long/smn_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 62 / 27 | `smn_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/smn_xivintheshell_long/smn_xivintheshell_damage.csv`; `results/calibration/smn_xivintheshell_long_skill_comparison.csv` | Audit demi / gem summon timing, pet or follow-up damage, elemental phases, and target attribution. |
| RDM | `examples/skill_lines/rdm_xivintheshell_long/rdm_xivintheshell_long.csv` | Manual xivintheshell long-axis candidate | 47 / 17 | `rdm_xivintheshell_long.json`; `source.md` | `import_smoke_passed`; `xivintheshell_damage_compared` | `examples/skill_lines/rdm_xivintheshell_long/rdm_xivintheshell_damage.csv`; `results/calibration/rdm_xivintheshell_long_skill_comparison.csv` | Audit mana spend, melee combo, Verflare / Verholy / Scorch / Resolution chain, and Embolden timing. |

## Immediate Task H Work Items

- Replace or supplement the manual long-axis candidates with real fight / log-sourced axes where available; current xivintheshell damage-export comparisons are a reproducible baseline, not a real-log substitute.
- Preserve each xivintheshell Record JSON and any target list or source note next to the CSV.
- Detailed xivintheshell damage exports and per-skill comparison tables now exist for MNK / DRG / VPR / BRD / MCH / DNC / SMN / RDM.
- Task I audit now exists at `docs/task_i_xivintheshell_comparison_audit.md`; attribution fixes for SMN pet/demi/gem rows, MCH Queen/Wildfire/Detonator rows, source-aware DoT aggregation, and RDM caster auto-attacks are implemented. Remaining rows are recorded as evidence boundaries: SMN manual-axis legality, MCH Heat Blast xivintheshell export gap, auto-attack timing drift, and smaller count-delta reviews for stronger future xivintheshells.
- Task J warning details now flow from `JobState.warn(...)` through the simulator result package, GUI report text, comparison summary, and per-job warning CSVs.
- Task K UI/report cleanup uses `src/ffxiv_ndps_simulator/sim.py` as the maintained GUI entrypoint, with `src/ffxiv_ndps_simulator/sim_test.py` kept only as a compatibility launcher. Runtime reports now show nDPS/RD definition, evidence level, sample path, target source, resource legality, and export Markdown/CSV evidence bundles.
- Keep BLM cleanup separate: the current best sample lives under `examples/skill_lines/sam_m9_m12s/sam_misc`, so moving it should be done with path xivintheshell updates.

## Regression Commands

```powershell
.\.venv\Scripts\python.exe scripts\scan_skill_coverage.py examples/skill_lines --issues-only --show-skills
.\.venv\Scripts\python.exe scripts\compare_xivintheshell_damage.py
.\.venv\Scripts\python.exe scripts\audit_xivintheshell_comparisons.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\smoke_damage_formula.py
```

## Caveats

- Short smoke openers prove parser and state-machine reachability, not long-fight numerical accuracy.
- Manual xivintheshell long-axis candidates are regression assets, not log validation.
- Historical long axes are not automatically log validated; they still need skill-level external totals.
- Until a job reaches `mechanic_calibrated` or `log_validated`, reports should avoid wording like "numerically verified".
