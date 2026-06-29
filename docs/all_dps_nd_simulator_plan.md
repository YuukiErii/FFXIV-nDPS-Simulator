# All-DPS nDPS Simulator Plan

Updated: 2026-06-29

This file remains the routing artifact for the all-DPS simulator plan. The original long plan was archived to `docs/archive/all_dps_nd_simulator_plan_2026_05_28.md`; the current consolidated status, evidence map, and folder policy now live in `docs/PROJECT_STATUS.md`.

## Current Phase Map

- Phase 0: baseline preservation and input-layer stabilization - complete.
- Phase 1: exact damage formula module - complete for the MVP evidence boundary.
- Phase 2: generic simulator core split - complete.
- Phase 3: skill coverage reporting - complete.
- Phase 4: DPS job-state MVP coverage - complete for all 13 DPS jobs.
- Task I: xivintheshell per-skill calibration triage - closed for the current plan scope.
- Task J: warning-only resource legality system - closed for the current plan scope.
- Task K: UI, report, and export closure - closed.
- Task L: packaging, self-test, and release validation - closed.
- Task M: advanced nDPS and teammate contribution accounting - future work.
- NIN accuracy pass: mechanic-calibrated against the retained 506-second xivintheshell axis; see `docs/archive/nin_nd_accuracy_audit_2026_06_29.md`.

## Active Routing

1. For user-facing usage, read `docs/USER_MANUAL.md`.
2. For current project status, evidence boundaries, job matrix, and regression commands, read `docs/PROJECT_STATUS.md`.
3. For historical task detail, use the archive index in `docs/PROJECT_STATUS.md`.
4. For generated Task I detail, run `scripts/audit_xivintheshell_comparisons.py` or inspect `docs/archive/task_i_xivintheshell_comparison_audit.md`.

## Conservative Claim Boundary

The MVP supports all 13 DPS jobs at the "axis can be imported, interpreted, warned on, simulated, and exported" level. Import smoke and xivintheshell comparison assets are useful regression evidence, but they are not FFLogs-equivalent validation. Avoid describing a job as `log_validated` unless it has real-log, AMAS, or externally audited equivalent evidence.

## Next Work Choices

- If continuing calibration, start from `docs/PROJECT_STATUS.md` and pick one job's next calibration focus.
- If changing simulator behavior, run the layer-specific regression commands in `docs/PROJECT_STATUS.md`.
- If changing UI or packaging, keep `src/ffxiv_ndps_simulator/sim.py` as the calculation source of truth and treat `apps/ndps-ui` as the presentation/desktop shell.
- If cleaning docs or folders, keep this route file, `docs/USER_MANUAL.md`, and `docs/PROJECT_STATUS.md` as the active document set.
