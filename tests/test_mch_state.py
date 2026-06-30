import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.mch import MchJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver, normalize_skill_name_for_job  # noqa: E402
from xiv_axis_csv import parse_axis_csv  # noqa: E402


BASE_STATS = {
    "job": "MCH",
    "main_stat": 5925,
    "crt": 3387,
    "det": 2407,
    "dh": 1935,
    "sks": 420,
    "wd": 152,
}


class MchJobStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = SkillResolver("MCH", "7.5")
        if cls.resolver.provider is None:
            raise unittest.SkipTest("AMAS skill provider is unavailable")

    def use(self, state, name, t=0.0):
        skill = self.resolver.get(name)
        state.set_event_context({})
        press_state = state.on_press(name, skill, t, t)
        payload = {"is_gcd": skill.get("is_gcd"), "targets": 1, **press_state}
        state.on_press_confirmed(name, skill, t, payload)
        potency, is_combo = state.resolve_potency(name, skill, t, payload)
        state.on_damage_resolved(name, skill, t + skill.get("delay", 0.0), is_combo, payload)
        return payload, potency

    def test_barrel_hypercharged_overheat_and_ready_states(self):
        state = MchJobState()
        self.use(state, "Barrel Stabilizer")
        self.assertEqual(state.heat, 0)
        self.assertGreater(state.hypercharged_until, 0)
        self.assertGreater(state.full_metal_ready_until, 0)

        self.use(state, "Hypercharge", 0.1)
        self.assertEqual(state.overheated_stacks, 5)
        self.assertLess(state.hypercharged_until, 0)
        self.assertNotIn("mch_heat_low", {w["code"] for w in state.get_resource_warnings()})

        _payload, potency = self.use(state, "Heat Blast", 0.2)
        self.assertEqual(potency, 220)
        self.assertEqual(state.overheated_stacks, 4)
        for i in range(4):
            self.use(state, "Heat Blast", 0.3 + i)
        self.assertEqual(state.overheated_stacks, 0)
        self.use(state, "Heat Blast", 5.0)
        self.assertIn("mch_heat_blast_no_overheat", {w["code"] for w in state.get_resource_warnings()})

        self.use(state, "Full Metal Field", 6.0)
        self.assertLess(state.full_metal_ready_until, 0)
        self.use(state, "Chain Saw", 7.0)
        self.assertGreater(state.excavator_ready_until, 0)
        self.use(state, "Excavator", 8.0)
        self.assertLess(state.excavator_ready_until, 0)
        self.use(state, "Excavator", 9.0)
        self.assertIn("mch_excavator_not_ready", {w["code"] for w in state.get_resource_warnings()})

    def test_combo_resources_and_queen_battery_scaled_followups(self):
        state = MchJobState()
        self.use(state, "Heated Split Shot", 0.0)
        self.use(state, "Heated Slug Shot", 2.5)
        self.use(state, "Heated Clean Shot", 5.0)
        self.assertEqual(state.heat, 15)
        self.assertEqual(state.battery, 10)

        state.battery = 60
        queen = self.resolver.get("Automaton Queen")
        payload = state.on_press("Automaton Queen", queen, 10.0, 10.0)
        followups = state.followup_damage_events("Automaton Queen", queen, 10.0, payload)
        self.assertEqual(
            [(x["name"], x["potency"]) for x in followups],
            [
                ("Roller Dash", 288),
                ("Armpunch", 144),
                ("Armpunch", 144),
                ("Armpunch", 144),
                ("Armpunch", 144),
                ("Armpunch", 144),
                ("Pilebunker", 408),
                ("Crowned Collider", 468),
            ],
        )

    def test_reassemble_does_not_affect_full_metal_field(self):
        state = MchJobState()
        self.use(state, "Reassemble", 0.0)
        state.full_metal_ready_until = 10.0
        full_metal = self.resolver.get("Full Metal Field")
        payload = state.on_press("Full Metal Field", full_metal, 1.0, 1.0)
        self.assertNotIn("guaranteed_crit", payload)
        self.assertTrue(state.reassemble_ready)

        drill = self.resolver.get("Drill")
        payload = state.on_press("Drill", drill, 2.0, 2.0)
        self.assertTrue(payload["guaranteed_crit"])
        self.assertTrue(payload["guaranteed_dh"])
        self.assertFalse(state.reassemble_ready)

    def test_flamethrower_ticks_and_cancels_on_next_action(self):
        state = MchJobState()
        flamethrower = self.resolver.get("Flamethrower")
        payload, potency = self.use(state, "Flamethrower", 0.0)
        self.assertEqual(potency, 0)

        ticks = state.followup_damage_events("Flamethrower", flamethrower, 0.0, {**payload, "targets": 2})
        self.assertEqual(len(ticks), 11)
        self.assertEqual(ticks[0]["delay"], 0.0)
        self.assertEqual(ticks[-1]["delay"], 10.0)
        self.assertTrue(all(tick["is_dot"] for tick in ticks))
        self.assertTrue(all(tick["potency"] == 120 for tick in ticks))
        self.assertTrue(state.is_followup_active(ticks[2], 2.0))
        self.assertFalse(state.allows_auto_attack_at(2.0))

        self.use(state, "Drill", 2.5)
        self.assertFalse(state.is_followup_active(ticks[3], 3.0))
        self.assertTrue(state.allows_auto_attack_at(3.0))

    def test_detonator_resolves_wildfire_early_under_wildfire_name(self):
        state = MchJobState()
        wildfire = self.resolver.get("Wildfire")
        state.on_press("Wildfire", wildfire, 0.0, 0.0)
        state.on_press_confirmed("Wildfire", wildfire, 0.0, {})
        state.wildfire_hits = 4

        detonator = self.resolver.get("Detonator")
        payload = state.on_press("Detonator", detonator, 5.0, 5.0)
        potency, is_combo = state.resolve_potency("Detonator", detonator, 5.0, payload)
        self.assertEqual(potency, 0)
        state.on_damage_resolved("Detonator", detonator, 5.0, is_combo, payload)
        followups = state.followup_damage_events("Detonator", detonator, 5.0, payload)
        self.assertEqual(followups[0]["name"], "Wildfire")
        self.assertEqual(followups[0]["potency"], 960)
        self.assertTrue(followups[0]["force_no_crit"])
        self.assertTrue(followups[0]["force_no_dh"])
        self.assertFalse(state.should_resolve_damage("Wildfire", wildfire, 10.0, {}))

    def test_mch_long_axis_has_tracked_resources(self):
        path = REPO_ROOT / "examples" / "skill_lines" / "mch_xivintheshell_long" / "mch_xivintheshell_long.csv"
        events, _meta = parse_axis_csv(
            path,
            normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, "MCH"),
        )
        result = DpsSimulator(dict(BASE_STATS), events, iterations=1).run_one_simulation(is_first_run=True)
        self.assertGreater(result[0], 0)
        self.assertEqual(result[-1], [])


if __name__ == "__main__":
    unittest.main()
