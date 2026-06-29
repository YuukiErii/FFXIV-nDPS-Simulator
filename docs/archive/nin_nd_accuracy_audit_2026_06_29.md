# NIN nDPS Accuracy Audit

Updated: 2026-06-30

## Result

NIN is now `mechanic_calibrated` for the local personal-nDPS boundary. The simulator models the current level-100 output kit, supports patch-specific potency data from 7.2 through 7.5, and replays the retained xivintheshell axis without false legality warnings. This is not yet an FFLogs-level numerical validation claim.

## Modeled Skills

| Family | Skills |
| --- | --- |
| Single-target combo | Spinning Edge, Gust Slash, Aeolian Edge, Armor Crush |
| Ranged and area weaponskills | Throwing Dagger, Death Blossom, Hakke Mujinsatsu |
| Mudra inputs | Ten, Chi, Jin |
| Ninjutsu | Fuma Shuriken, Katon, Raiton, Hyoton, Huton, Doton, Suiton |
| Kassatsu ninjutsu | Goka Mekkyaku, Hyosho Ranryu |
| Core abilities | Hide, Kassatsu, Ten Chi Jin, Meisui, Bunshin, True North |
| Direct output | Dokumori, Kunai's Bane, Dream Within a Dream |
| Ninki spenders | Bhavacakra, Hellfrog Medium, Zesho Meppo, Deathfrog Medium, Bunshin |
| Ready actions | Phantom Kamaitachi, Forked Raiju, Fleeting Raiju, Tenri Jindo |
| Generated output | Hollow Nozuchi and Bunshin shadow hits |

TCJ-labelled rows such as `Fuma Shuriken (Ten)`, `Raiton (Chi)`, and `Suiton (Jin)` are resolved as the same damage skills while retaining their mudra-button identity for sequence validation.

## Modeled Output Mechanics

- Ninki gains and 50-point spending occur at action confirmation; overcap and insufficient-gauge cases are reported without blocking the replay.
- Ninjutsu, mudra, Throwing Dagger, Raiju, and Phantom Kamaitachi preserve the melee combo. Melee weaponskills correctly clear Raiju Ready.
- Aeolian Edge and Armor Crush use successful positionals by default. `positionalHit=false` models a miss, while True North overrides it.
- Armor Crush grants two Kazematoi stacks up to five; Aeolian Edge consumes one stack for 100 additional potency.
- Mudra order, duplicate mudra, interruption, rabbit failure, Kassatsu upgrades, TCJ order, TCJ action lock, and readiness consumption are tracked.
- Suiton and Huton grant Shadow Walker. Kunai's Bane accepts Hidden or Shadow Walker; Meisui requires Shadow Walker specifically.
- Dokumori grants 40 Ninki and Higi. Higi, Meisui, Phantom, Raiju, Tenri, Kassatsu, Shadow Walker, and Bunshin all have explicit durations and consumption.
- Dokumori, Kunai's Bane, and Trick Attack begin their damage-taken debuffs after their own hit, so the applying action does not benefit from its own debuff. Their modeled server windows are 21.00s, 16.25s, and 15.77s respectively.
- Bunshin has five stacks and emits independent 160-potency single-target/ranged or 80-potency area shadow hits using the pet job modifier. Each shadow hit also grants 5 Ninki. Shadow hits count for damage and attribution but do not extend the axis denominator when the external export folds them into the triggering hit.
- Phantom Kamaitachi uses pet damage classification and the pet job modifier, grants 10 Ninki, and can trigger Hollow Nozuchi.
- Dream Within a Dream is three 180-potency hits. The three hits roll damage variance separately, while sharing the same critical/direct-hit result for the cast.
- Doton has no direct hit. It creates an 18-second ground DoT, can be placed while the target is unavailable, snapshots Kassatsu's 30% bonus, triggers Hollow Nozuchi from the documented actions, and ends on Hide.
- NIN's 15% inherent haste is applied to GCD and auto-attack cadence. The default NIN weapon delay is 2.56.
- Patch data remains version-aware, including Dokumori, Kunai's Bane, Goka Mekkyaku, spenders, Phantom Kamaitachi, Hollow Nozuchi, and area falloff changes.

## Closed Accuracy Gaps

1. Replaced the former partial buff-only state with full Ninki, combo, Kazematoi, mudra, readiness, and spender state.
2. Corrected Ninki timing and preserved combos across Ninjutsu.
3. Added Bunshin and Dream Within a Dream generated hits instead of treating them as one parent hit.
4. Added pet job-modifier propagation for Phantom Kamaitachi and Bunshin.
5. Removed Doton's false direct hit and added Kassatsu snapshot, Hollow Nozuchi, downtime placement, and Hide cancellation.
6. Corrected Hidden versus Shadow Walker legality for Meisui.
7. Corrected patch ordering so `7.5` receives changes introduced in `7.25`.
8. Delayed Dokumori and Kunai's Bane debuff activation until after their own damage.
9. Added successful positionals as the default with an explicit per-row miss override.
10. Corrected the default weapon delay from the generic 2.64 to NIN's 2.56, closing the 226-versus-233 auto-attack count drift.
11. Corrected NIN debuff windows to match the xivintheshell/Balance timing model.
12. Split follow-up damage processing from duration accounting so the retained 506.341-second axis keeps the same denominator as the external PPS export while still counting Bunshin shadow damage.

## External Comparison

The retained sample contains 409 axis actions and 534 xivintheshell damage rows. All pressed damaging skills match external event counts. Auto-attacks now match at 233.

Two attribution differences are intentional:

- xivintheshell exports Dream Within a Dream as one 540-potency row per cast; the local simulator keeps the official three 180-potency damage rolls with shared critical/direct-hit state.
- xivintheshell folds Bunshin potency into its triggering weaponskill; the local simulator emits 30 independently attributed pet hits.

The external damage export totals 203079.7456 adjusted potency over 506.34125 seconds, i.e. 401.072884 PPS. Local duration accounting preserves that 506.34125-second denominator; the final Bunshin shadow event after the last Fleeting Raiju is processed for damage but not used as the denominator endpoint.

The two remaining warnings in the sample are real Ninki overcaps at rows 105 and 373, not missing-state errors.

Evidence:

- `examples/skill_lines/nin_m12s_p2/nin_830.txt`
- `examples/skill_lines/nin_m12s_p2/nin_830.csv`
- `examples/skill_lines/nin_m12s_p2/nin_830_damage.csv`
- `results/calibration/nin_xivintheshell_long_skill_comparison.csv`
- `results/calibration/nin_resource_warnings.csv`
- `tests/test_nin_state.py`
