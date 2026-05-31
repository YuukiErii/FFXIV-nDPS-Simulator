# SAM Backup vs Stable RD Regression Audit

Date: 2026-05-31

## Scope

This audit compares the maintained simulator core in
`src/ffxiv_ndps_simulator/sim.py` with the preserved SAM-only baseline in
`archive/legacy_source/sam_only_sim_test_20260527.py`.

The backup result is treated as authoritative for this regression audit.

Shared input:

- Axis: `examples/skill_lines/sam_m9_m12s/m9s_final.csv`
- Rows: `392`
- Stats: `STR=6498`, `CRT=3605`, `DET=2426`, `DH=1793`, `SKS=689`,
  `WD=158`, `delay=2.64`, `party_bonus=1.05`
- Iterations: `1000`
- Random seed: `20260531`
- Mode: single target, no extra downtime configuration

## Direct Comparison

| Simulator | Mean RD | Std Dev | Duration | Last Hit | Auto Attacks | Resource Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SAM-only backup | 41304.66 | 430.66 | 516.959s | 516.959s | 209 | 0 |
| Maintained stable core | 37515.14 | 397.92 | 516.959s | 516.959s | 202 | 42 |
| Delta | -3789.51 | -32.74 | 0 | 0 | -7 | +42 |

The stable core is `9.17%` below the backup baseline. The equal duration and
last-hit timestamp rule out an RD denominator or CSV-import failure.

## Ablation Results

The following diagnostic-only monkeypatches were applied in memory. No runtime
source file was changed.

| Variant | Mean RD | Delta vs Backup | Delta % |
| --- | ---: | ---: | ---: |
| SAM-only backup | 41307.21 | 0.00 | 0.000% |
| Stable current behavior | 37518.91 | -3788.30 | -9.171% |
| Stable with local SAM skill table only | 40103.69 | -1203.52 | -2.914% |
| Stable with provider data plus backup combo transitions | 38607.33 | -2699.88 | -6.536% |
| Stable with local SAM skill table plus backup combo transitions | 41299.63 | -7.58 | -0.018% |

The final variant returns to the backup baseline within sampling noise. This
isolates two independent regressions.

## Root Cause 1: Provider Data Replaces SAM Overlay Data

`SkillResolver.get(...)` returns AMAS provider data before checking the local
SAM `SKILL_DB`. The provider response is not merged with the local SAM overlay.

The local table carries simulator-specific fields that the provider does not:

- `Gekko` / `月光`: `meikyo_grants="fugetsu"`
- `Kasha` / `花车`: `meikyo_grants="shifu"`

As a result, opening `Meikyo Shisui -> Gekko` no longer grants Fugetsu. The
stable event log immediately shows `Higanbana` without the expected Fugetsu
buff. Losing the Meikyo-applied Shifu window also reduces auto attacks from
`209` to `202`.

Provider-first resolution also changes backup-authoritative SAM values:

- `Midare Setsugekka`: `680 -> 640`
- `Kaeshi: Setsugekka`: `680 -> 640`
- non-combo `Gekko` / `Kasha`: `200 -> 210`
- `Yukikaze` application delay: `0.85 -> 0.80`
- `Ogi Namikiri` secondary-target decay: `0.40 -> 0.50`

Some provider values may reflect a different upstream patch, but they must not
silently replace the SAM backup baseline while that baseline is authoritative.

Relevant code:

- `src/ffxiv_ndps_simulator/sim.py:369-385`
- `src/ffxiv_ndps_simulator/sim.py:84-87`
- `src/ffxiv_ndps_simulator/jobs/sam.py:102-109`

## Root Cause 2: Damage Abilities Break the GCD Combo Chain

The migrated SAM state updates `combo_action` for every positive-potency skill:

```python
if skill.get("potency", 0) > 0 or skill.get("combo_prev") or name == "晓风":
    self.combo_action = name
```

This means an inserted oGCD damage ability, such as `Hissatsu: Shinten`, replaces
the previous GCD combo action. A later `Gekko`, `Kasha`, or `Yukikaze` can then
be resolved at non-combo potency.

The backup only advances or clears combo state on the relevant GCD combo
transitions. Restoring that behavior removes the remaining SAM RD drift.

The generic `JobState` implementation uses the same broad update policy, so
other combo-based jobs that call `super().on_damage_resolved(...)` need an audit.

Relevant code:

- `src/ffxiv_ndps_simulator/jobs/sam.py:111-113`
- `src/ffxiv_ndps_simulator/jobs/base.py:54-58`
- `archive/legacy_source/sam_only_sim_test_20260527.py:513-526`

## Non-Root-Cause Reporting Difference

The maintained core attributes Higanbana ticks back to `彼岸花`, while the
backup aggregates them under `Dot Tick`. This is a useful reporting improvement,
not the main regression:

| Bucket | Backup RD | Stable RD |
| --- | ---: | ---: |
| `Dot Tick` | 1800.97 | 0.00 |
| `彼岸花` | 394.01 | 2080.97 |

The combined Higanbana difference is much smaller than the total RD gap and is
explained by the missing Fugetsu snapshot windows.

## Why Existing Tests Passed

`tests/test_all_job_states.py` uses only:

```text
Hakaze -> Jinpu -> Gekko
```

for the SAM smoke path. It contains no Meikyo window and no inserted oGCD.
The assertion only checks that duration and total damage are positive.

The source and packaged `--self-test` paths also passed on 2026-05-31 because
historical CSV smoke still checks positive output rather than a frozen
backup-authoritative replay value.

## Recommended Fix Slice

1. Add a SAM-specific overlay merge after AMAS provider lookup. Keep the backup
   SAM values and simulator-only fields authoritative until deliberately
   recalibrated.
2. Restrict combo-state updates to valid combo-chain GCD transitions. Audit the
   generic `JobState` rule for other combo jobs.
3. Add targeted tests for `Meikyo Shisui -> Gekko`, `Gyofu -> Jinpu -> oGCD ->
   Gekko`, and the frozen long-axis SAM replay baseline.
4. Rebuild the packaged EXE only after source tests and the backup replay gate
   pass.
