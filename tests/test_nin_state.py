import pathlib
import random
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.nin import NinJobState  # noqa: E402
from sim import (  # noqa: E402
    DpsSimulator,
    SkillResolver,
    TINCTURE_STR,
    build_skill_coverage,
    normalize_skill_name_for_job,
)
from xiv_axis_csv import parse_axis_csv  # noqa: E402
from xiv_damage_formula import DamageModifiers, FormulaStats, XivDamageFormula  # noqa: E402
from xiv_job_data import DEFAULT_MAIN_STATS  # noqa: E402


BASE_STATS = {
    "job": "NIN",
    "version": "7.5",
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "delay": 2.56,
}


def confirm(state, resolver, name, current_time, event=None):
    event = dict(event or {})
    skill = resolver.get(name)
    if skill is None:
        raise AssertionError(f"Missing NIN skill data: {name}")
    state.set_event_context(event)
    press_state = state.on_press(name, skill, current_time, current_time)
    payload = {"tid": 1, "targets": 1, **event, **press_state}
    state.on_press_confirmed(name, skill, current_time, payload)
    return skill, payload


class NinJobStateTests(unittest.TestCase):
    def test_positionals_default_to_hit_and_allow_explicit_miss(self):
        resolver = SkillResolver("NIN", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        def aeolian_potency(positional_hit=None, true_north=False):
            state = NinJobState("7.5")
            if true_north:
                confirm(state, resolver, "True North", 0.0)
            state.combo_action = "Gust Slash"
            state.combo_time = 0.0
            state.kazematoi = 1
            event = {} if positional_hit is None else {"positional_hit": positional_hit}
            skill, payload = confirm(state, resolver, "Aeolian Edge", 1.0, event)
            return state.resolve_potency("Aeolian Edge", skill, 1.5, payload)[0]

        self.assertEqual(aeolian_potency(), 560)
        self.assertEqual(aeolian_potency(False), 500)
        self.assertEqual(aeolian_potency(False, true_north=True), 560)

    def test_axis_positional_column_preserves_default_and_explicit_miss(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "nin.csv"
            path.write_text(
                "time,action,positionalHit\n"
                "0,Aeolian Edge,false\n"
                "2.5,Armor Crush,\n",
                encoding="utf-8",
            )
            entries, meta = parse_axis_csv(path)

        self.assertFalse(entries[0]["positional_hit"])
        self.assertIsNone(entries[1]["positional_hit"])
        self.assertTrue(meta["has_positional_hit"])

    def test_ninjutsu_preserves_combo_and_tcj_sequence_is_validated(self):
        resolver = SkillResolver("NIN", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = NinJobState("7.5")
        state.combo_action = "Spinning Edge"
        state.combo_time = 0.0
        confirm(state, resolver, "Ten", 0.1)
        confirm(state, resolver, "Chi", 0.2)
        raiton, raiton_payload = confirm(state, resolver, "Raiton", 0.3)
        state.on_damage_resolved("Raiton", raiton, 0.8, False, raiton_payload)
        gust, gust_payload = confirm(state, resolver, "Gust Slash", 1.0)
        gust_potency, gust_combo = state.resolve_potency("Gust Slash", gust, 1.5, gust_payload)
        state.on_damage_resolved("Gust Slash", gust, 1.5, gust_combo, gust_payload)
        aeolian, aeolian_payload = confirm(state, resolver, "Aeolian Edge", 2.0)
        _, aeolian_combo = state.resolve_potency("Aeolian Edge", aeolian, 2.5, aeolian_payload)

        self.assertEqual(gust_potency, 400)
        self.assertTrue(gust_combo)
        self.assertTrue(aeolian_combo)
        self.assertEqual(state.ninki, 20)
        self.assertEqual(state.raiju_stacks, 0)

        tcj_state = NinJobState("7.5")
        confirm(tcj_state, resolver, "Ten Chi Jin", 3.0)
        confirm(tcj_state, resolver, "Fuma Shuriken (Ten)", 3.1)
        confirm(tcj_state, resolver, "Raiton (Chi)", 3.2)
        confirm(tcj_state, resolver, "Suiton (Jin)", 3.3)
        warning_codes = {item["code"] for item in tcj_state.get_resource_warnings()}
        self.assertFalse(any(code.startswith("nin_tcj_") for code in warning_codes))
        self.assertGreater(tcj_state.tenri_ready_until, 3.3)
        self.assertFalse(tcj_state._active(tcj_state.ten_chi_jin_until, 3.3))

    def test_doton_kassatsu_hollow_nozuchi_and_hide(self):
        resolver = SkillResolver("NIN", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = NinJobState("7.5")
        state.kassatsu_until = 10.0
        state.mudra_sequence = ["Ten", "Jin", "Chi"]
        state.mudra_until = 10.0
        doton, payload = confirm(state, resolver, "Doton", 0.0)
        potency, is_combo = state.resolve_potency("Doton", doton, 0.5, payload)
        dots = state.dot_applications("Doton", doton, 0.5, 2, 1, {}, False)
        state.on_damage_resolved(
            "Doton",
            doton,
            0.5,
            is_combo,
            {**payload, "damage_immune": True},
        )

        self.assertEqual(potency, 0)
        self.assertEqual(dots[0]["potency"], 104)
        self.assertEqual(dots[0]["targets"], 2)
        self.assertTrue(state.is_dot_active({"dot_key": "Doton", "tid": 1}, 1.0))
        hollow = state.followup_damage_events(
            "Katon",
            resolver.get("Katon"),
            1.0,
            {"tid": 1, "targets": 2},
        )
        self.assertEqual(hollow[0]["potency"], 70)
        self.assertEqual(hollow[0]["targets"], 2)

        confirm(state, resolver, "Hide", 1.1)
        self.assertFalse(state.is_dot_active({"dot_key": "Doton", "tid": 1}, 1.2))

        old_state = NinJobState("7.2")
        old_state.doton_until[1] = 10.0
        old_hollow = old_state.followup_damage_events(
            "Katon",
            SkillResolver("NIN", "7.2").get("Katon"),
            1.0,
            {"tid": 1, "targets": 1},
        )
        self.assertEqual(old_hollow[0]["potency"], 50)

    def test_doton_can_be_placed_during_downtime_and_tick_after_return(self):
        timeline = [
            (0.2, "Ten", 1),
            (0.4, "Jin", 1),
            (0.6, "Chi", 1),
            (1.0, "Doton", 1),
            (5.0, "Throwing Dagger", 1),
        ]
        random.seed(1)
        result = DpsSimulator(
            BASE_STATS,
            timeline,
            iterations=1,
            global_downtime_list=[(0.0, 2.0)],
        ).run_one_simulation()
        self.assertGreaterEqual(result[3]["Doton"], 2)

    def test_meisui_requires_shadow_walker_not_hidden(self):
        resolver = SkillResolver("NIN", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        hidden_state = NinJobState("7.5")
        hidden_state.hidden_until = float("inf")
        confirm(hidden_state, resolver, "Meisui", 0.0)
        self.assertIn(
            "nin_shadow_walker_missing",
            {item["code"] for item in hidden_state.get_resource_warnings()},
        )

        shadow_state = NinJobState("7.5")
        shadow_state.shadow_walker_until = 20.0
        confirm(shadow_state, resolver, "Meisui", 0.0)
        self.assertEqual(shadow_state.ninki, 50)
        self.assertFalse(shadow_state.get_resource_warnings())

    def test_tincture_ends_hidden_and_does_not_start_auto_attacks(self):
        timeline = [
            (-2.0, "Hide", 1),
            (0.0, "Tincture", 1),
            (3.0, "Kunai's Bane", 1),
        ]
        result = DpsSimulator(BASE_STATS, timeline, iterations=1).run_one_simulation()
        warning_codes = {item["code"] for item in result[12]}
        self.assertIn("nin_shadow_walker_missing", warning_codes)
        self.assertEqual(result[3]["Auto Attack"], 1)

    def test_damage_debuffs_start_after_their_own_hit(self):
        resolver = SkillResolver("NIN", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = NinJobState("7.5")
        dokumori, payload = confirm(state, resolver, "Dokumori", 0.0)
        self.assertEqual(state.active_damage_buffs(1.0)["damage_mult"], 1.0)
        state.on_damage_resolved(
            "Dokumori",
            dokumori,
            1.07,
            False,
            {**payload, "targets": 2},
        )
        self.assertAlmostEqual(state.active_damage_buffs(1.08)["damage_mult"], 1.05)
        self.assertAlmostEqual(state.active_damage_buffs(1.08, target_id=2)["damage_mult"], 1.05)
        self.assertAlmostEqual(state.active_damage_buffs(22.06)["damage_mult"], 1.05)
        self.assertEqual(state.active_damage_buffs(22.07)["damage_mult"], 1.0)

        state.shadow_walker_until = 30.0
        kunai, kunai_payload = confirm(state, resolver, "Kunai's Bane", 2.0)
        self.assertAlmostEqual(state.active_damage_buffs(3.0)["damage_mult"], 1.05)
        state.on_damage_resolved("Kunai's Bane", kunai, 3.29, False, kunai_payload)
        self.assertAlmostEqual(state.active_damage_buffs(3.30)["damage_mult"], 1.155)
        self.assertAlmostEqual(state.active_damage_buffs(19.53)["damage_mult"], 1.155)
        self.assertAlmostEqual(state.active_damage_buffs(19.54)["damage_mult"], 1.05)

    def test_versioned_potencies_pet_metadata_and_generated_hits(self):
        old = SkillResolver("NIN", "7.2")
        current = SkillResolver("NIN", "7.5")
        if current.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        self.assertEqual(old.get("Dokumori")["potency"], 300)
        self.assertEqual(current.get("Dokumori")["potency"], 400)
        self.assertEqual(old.get("Goka Mekkyaku")["potency"], 600)
        self.assertEqual(current.get("Goka Mekkyaku")["potency"], 850)
        phantom = current.get("Phantom Kamaitachi")
        self.assertEqual(phantom["potency"], 700)
        self.assertTrue(phantom["is_aoe"])
        self.assertEqual(phantom["decay"], 0)
        self.assertEqual(phantom["job_mod_override"], 100)

        timeline = [
            (0.0, "Dokumori", 1),
            (0.1, "Spinning Edge", 1),
            (0.2, "Throwing Dagger", 1),
            (0.3, "Bunshin", 1),
            (1.0, "Spinning Edge", 1),
            (2.0, "Dream Within a Dream", 1),
        ]
        random.seed(1)
        result = DpsSimulator(BASE_STATS, timeline, iterations=1).run_one_simulation()
        counts = result[3]
        warning_codes = {item["code"] for item in result[12]}
        self.assertEqual(counts["Spinning Edge (pet)"], 1)
        self.assertEqual(counts["Dream Within a Dream"], 3)
        self.assertNotIn("nin_ninki_low", warning_codes)

    def test_default_simulator_version_is_75(self):
        stats = dict(BASE_STATS)
        stats.pop("version")
        sim = DpsSimulator(stats, [(0.0, "Dokumori", 1)], iterations=1)
        self.assertEqual(sim.stats["version"], "7.5")
        self.assertEqual(sim.get_skill("Dokumori")["potency"], 400)

    def test_dream_followups_share_crit_direct_but_roll_variance_separately(self):
        random_values = iter([
            1.0, 1.0,  # Auto Attack before Dream: no crit, no DH.
            0.0, 1.0,  # Dream source roll: crit, no DH.
            1.0, 0.0,  # Would diverge if followups rolled crit/DH independently.
            1.0, 0.0,
        ])
        uniform_values = iter([
            2.5,   # Initial DoT tick scheduling.
            1.0,   # Auto Attack variance.
            0.95,  # Dream hit 1 variance.
            1.0,   # Dream hit 2 variance.
            1.05,  # Dream hit 3 variance.
        ])
        with patch.object(random, "random", side_effect=lambda: next(random_values)), \
                patch.object(random, "uniform", side_effect=lambda _low, _high: next(uniform_values)):
            result = DpsSimulator(BASE_STATS, [(0.0, "Dream Within a Dream", 1)], iterations=1) \
                .run_one_simulation(is_first_run=True)

        dream_rows = [row for row in result[8] if row["name"] == "Dream Within a Dream"]
        self.assertEqual(len(dream_rows), 3)
        self.assertEqual({row["crit"] for row in dream_rows}, {"✔"})
        self.assertEqual({row["dh"] for row in dream_rows}, {""})
        damages = [float(str(row["dmg"]).replace(",", "")) for row in dream_rows]
        self.assertEqual(len(set(damages)), 3)

    def test_nin_uses_job_weapon_delay_when_not_explicitly_overridden(self):
        stats = dict(BASE_STATS)
        stats.pop("delay")
        sim = DpsSimulator(stats, [(0.0, "Spinning Edge", 1)], iterations=1)
        self.assertEqual(sim.stats["delay"], 2.56)

    def test_nin_default_main_stat_is_6490(self):
        self.assertEqual(DEFAULT_MAIN_STATS["NIN"], 6490)

    def test_nin_potion_ap_matches_party_bonus_order(self):
        stats = dict(BASE_STATS)
        stats["main_stat"] = 6490
        stats["str"] = 6490
        stats["wd"] = 152
        stats["dh"] = 1961
        stats["det"] = 2527
        stats["sks"] = 420
        stats["delay"] = 2.56
        stats["version"] = "7.5"
        sim = DpsSimulator(stats, [(0.0, "Spinning Edge", 1)], iterations=1)
        formula = XivDamageFormula(
            FormulaStats.from_job("NIN", 6490, 3605, 2527, 1961, 420, 152, 2.56, 1.05)
        )
        potion_main = formula.final_main_stat(DamageModifiers(main_stat_add=TINCTURE_STR))
        self.assertEqual(sim.ap_val_potion, formula.f_ap(potion_main))

    def test_long_nin_axis_has_full_coverage_and_no_false_legality_warnings(self):
        path = REPO_ROOT / "examples" / "skill_lines" / "nin_m12s_p2" / "nin_830.csv"
        events, meta = parse_axis_csv(
            path,
            normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, "NIN"),
        )
        resolver = SkillResolver("NIN", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")
        report = build_skill_coverage(events, resolver, csv_meta=meta)
        self.assertEqual(report["stats"].get("unrecognized_events", 0), 0)
        self.assertEqual(report["stats"].get("needs_state_events", 0), 0)
        self.assertEqual(report["stats"].get("followup_unmodeled_events", 0), 0)

        random.seed(1)
        result = DpsSimulator(BASE_STATS, events, iterations=1).run_one_simulation()
        counts = result[3]
        warnings = result[12]
        self.assertAlmostEqual(result[1], 506.34125, places=5)
        self.assertEqual(counts["Dream Within a Dream"], 27)
        self.assertEqual(counts["Auto Attack"], 233)
        self.assertEqual(
            sum(count for name, count in counts.items() if name.endswith(" (pet)")),
            29,
        )
        self.assertEqual({item["code"] for item in warnings}, {"nin_ninki_overcap"})


if __name__ == "__main__":
    unittest.main()
