import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.rdm import RdmJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver  # noqa: E402


BASE_STATS = {
    "job": "RDM",
    "main_stat": 5925,
    "crt": 3456,
    "det": 1970,
    "dh": 1885,
    "sks": 547,
    "wd": 152,
}


class RdmStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = SkillResolver("RDM", "7.5")
        if cls.resolver.provider is None:
            raise unittest.SkipTest("AMAS skill provider is unavailable")

    def use(self, state, name, t=0.0):
        skill = self.resolver.get(name)
        default_cast = float(skill.get("cast", 0) or 0)
        cast = state.effective_cast_time(name, skill, {}, t, default_cast)
        snapshot = t if cast <= 0 else max(t, t + cast - 0.5)
        state.set_event_context({})
        press_state = state.on_press(name, skill, t, snapshot)
        payload = {"is_gcd": skill.get("is_gcd"), "targets": 1, **press_state}
        state.on_press_confirmed(name, skill, t, payload)
        potency, is_combo = state.resolve_potency(name, skill, t, payload)
        state.on_damage_resolved(name, skill, t + cast + skill.get("delay", 0.0), is_combo, payload)
        return potency, cast

    def test_dualcast_swiftcast_and_acceleration_control_cast_times(self):
        state = RdmJobState()
        self.use(state, "Jolt III")
        self.assertTrue(state.dualcast_until > 0)

        veraero = self.resolver.get("Veraero III")
        self.assertEqual(state.effective_cast_time("Veraero III", veraero, {}, 3.0, 5.0), 0.0)
        self.use(state, "Veraero III", 3.0)
        self.assertEqual(state.dualcast_until, -1.0)

        self.use(state, "Swiftcast", 6.0)
        self.assertEqual(state.effective_cast_time("Verthunder III", veraero, {}, 7.0, 5.0), 0.0)
        self.use(state, "Verthunder III", 7.0)
        self.assertEqual(state.dualcast_until, -1.0)

        self.use(state, "Acceleration", 10.0)
        impact = self.resolver.get("Impact")
        self.assertEqual(state.effective_cast_time("Impact", impact, {}, 11.0, 5.0), 0.0)
        potency, _cast = self.use(state, "Impact", 11.0)
        self.assertEqual(potency, 260)

    def test_manafication_grants_swordplay_not_mana(self):
        state = RdmJobState()
        state.black_mana = 0
        state.white_mana = 0
        self.use(state, "Manafication")

        self.assertEqual((state.black_mana, state.white_mana), (0, 0))
        self.assertEqual(state.magicked_swordplay_stacks, 3)
        self.assertTrue(state.prefulgence_ready_until > 0)

        for name in ["Enchanted Riposte", "Enchanted Zwerchhau", "Enchanted Redoublement"]:
            self.use(state, name)

        self.assertEqual((state.black_mana, state.white_mana), (0, 0))
        self.assertEqual(state.magicked_swordplay_stacks, 0)
        self.assertEqual(state.mana_stacks, 3)
        self.assertFalse([w for w in state.get_resource_warnings() if w["code"] == "rdm_mana_low"])

    def test_finishers_ready_states_and_mana_gains(self):
        state = RdmJobState()
        state.mana_stacks = 3
        self.use(state, "Verflare")
        self.assertEqual(state.mana_stacks, 0)
        self.assertEqual(state.black_mana, 61)

        self.use(state, "Scorch")
        self.use(state, "Resolution")
        self.assertEqual((state.black_mana, state.white_mana), (69, 58))

        self.use(state, "Embolden", 20.0)
        self.assertAlmostEqual(state.active_damage_buffs(21.0)["damage_mult"], 1.10)
        self.assertTrue(state.active_damage_buffs(40.94)["rdm_embolden"])
        self.assertFalse(state.active_damage_buffs(40.96)["rdm_embolden"])
        self.use(state, "Vice of Thorns", 21.0)
        self.assertEqual(state.thorned_flourish_until, -1.0)

        self.use(state, "Prefulgence", 22.0)
        self.assertIn("rdm_prefulgence_not_ready", {w["code"] for w in state.get_resource_warnings()})
        self.use(state, "Manafication", 30.0)
        self.use(state, "Prefulgence", 31.0)
        self.assertEqual(state.prefulgence_ready_until, -1.0)

    def test_sim_uses_spell_speed_for_implicit_rdm_casts(self):
        sim = DpsSimulator(dict(BASE_STATS), [], iterations=1)
        verthunder = self.resolver.get("Verthunder III")
        self.assertEqual(sim.effective_cast_time(verthunder, {}), 4.97)
        self.assertEqual(sim.effective_cast_time(verthunder, {"cast_time": 5.0}), 5.0)

    def test_embolden_only_buffs_rdm_magical_damage(self):
        state = RdmJobState()
        self.use(state, "Embolden", 20.0)
        buffs = state.active_damage_buffs(21.0)

        physical = state.filter_active_damage_buffs("Fleche", self.resolver.get("Fleche"), buffs)
        self.assertFalse(physical["rdm_embolden"])
        self.assertAlmostEqual(physical["damage_mult"], 1.0)
        self.assertEqual(physical["damage_factors"], [])

        displacement = state.filter_active_damage_buffs("Displacement", self.resolver.get("Displacement"), buffs)
        self.assertFalse(displacement["rdm_embolden"])
        self.assertAlmostEqual(displacement["damage_mult"], 1.0)

        enchanted = state.filter_active_damage_buffs(
            "Enchanted Riposte", self.resolver.get("Enchanted Riposte"), buffs
        )
        self.assertTrue(enchanted["rdm_embolden"])
        self.assertAlmostEqual(enchanted["damage_mult"], 1.10)

        auto = state.filter_active_damage_buffs("Auto Attack", {"potency": 90}, buffs)
        self.assertFalse(auto["rdm_embolden"])
        self.assertAlmostEqual(auto["damage_mult"], 1.0)

    def test_sim_log_removes_embolden_from_physical_rdm_skills(self):
        sim = DpsSimulator(
            dict(BASE_STATS),
            [(0.0, "Embolden", 1), (1.0, "Fleche", 1), (2.0, "Jolt III", 1)],
            iterations=1,
        )
        _dps_list, _sim_dur, _last_hit, _stats_pkg, log = sim.run_batch()
        rows = {row["name"]: row for row in log}
        self.assertEqual(rows["Fleche"]["buffs"], "-")
        self.assertIn("鼓励", rows["Jolt III"]["buffs"])

    def test_inactive_embolden_is_not_active_before_pull(self):
        state = RdmJobState()
        buffs = state.active_damage_buffs(-2.0)

        self.assertFalse(buffs["rdm_embolden"])
        self.assertFalse(buffs["rdm_dualcast"])
        self.assertEqual(buffs["damage_factors"], [])
        self.assertAlmostEqual(buffs["damage_mult"], 1.0)

    def test_acceleration_potency_label_matches_planner(self):
        sim = DpsSimulator(
            dict(BASE_STATS),
            [(0.0, "Acceleration", 1), (1.0, "Impact", 2)],
            iterations=1,
        )
        _dps_list, _sim_dur, _last_hit, _stats_pkg, log = sim.run_batch()
        impact = [row for row in log if row["name"] == "Impact"][0]
        self.assertEqual(impact["potency_buffs"], "促进")

    def test_melee_combo_is_snapshotted_before_interleaved_manafication(self):
        sim = DpsSimulator(
            dict(BASE_STATS),
            [
                (0.0, "Enchanted Riposte", 1),
                (1.5, "Enchanted Zwerchhau", 1),
                (3.0, "Enchanted Redoublement", 1),
                (3.1, "Manafication", 1),
            ],
            iterations=1,
        )
        _dps_list, _sim_dur, _last_hit, _stats_pkg, log = sim.run_batch()
        redoublement = [row for row in log if row["name"] == "Enchanted Redoublement"][0]
        self.assertEqual(redoublement["potency"], 560)
        self.assertNotIn("技能状态", redoublement["potency_buffs"])


if __name__ == "__main__":
    unittest.main()
