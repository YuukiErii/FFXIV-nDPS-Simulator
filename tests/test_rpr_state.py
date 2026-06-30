import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.rpr import RprJobState  # noqa: E402
from sim import SkillResolver  # noqa: E402


def use(state, resolver, name, current_time):
    skill = resolver.get(name)
    if skill is None:
        raise AssertionError(f"Missing RPR skill data: {name}")
    state.set_event_context({})
    press_state = state.on_press(name, skill, current_time, current_time)
    payload = {
        "tid": 1,
        "targets": 1,
        "is_gcd": skill.get("is_gcd"),
        **press_state,
    }
    state.on_press_confirmed(name, skill, current_time, payload)
    potency, is_combo = state.resolve_potency(name, skill, current_time + skill.get("delay", 0), payload)
    state.on_damage_resolved(name, skill, current_time + skill.get("delay", 0), is_combo, payload)
    return potency


class RprJobStateTests(unittest.TestCase):
    def test_full_burst_chain_uses_default_eight_sacrifice_stacks(self):
        resolver = SkillResolver("RPR", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = RprJobState()
        self.assertEqual(state.immortal_sacrifice, 8)
        self.assertTrue(state.soulsow_ready)

        self.assertEqual(use(state, resolver, "Plentiful Harvest", 0.0), 1000)
        self.assertGreater(state.ideal_host, 0.0)
        self.assertGreater(state.perfectio_occulta, 0.0)

        state.shroud = 0
        use(state, resolver, "Enshroud", 2.5)
        self.assertEqual(state.shroud, 0)
        self.assertEqual(state.lemure_shroud, 5)
        self.assertEqual(state.oblatio, 1)

        self.assertEqual(use(state, resolver, "Sacrificium", 3.0), 700)
        self.assertEqual(state.oblatio, 0)
        self.assertEqual(use(state, resolver, "Void Reaping", 3.5), 580)
        self.assertEqual(state.lemure_shroud, 4)
        self.assertEqual(state.void_shroud, 1)
        self.assertEqual(use(state, resolver, "Cross Reaping", 5.0), 640)
        self.assertEqual(state.lemure_shroud, 3)
        self.assertEqual(state.void_shroud, 2)
        use(state, resolver, "Lemure's Slice", 5.5)
        self.assertEqual(state.void_shroud, 0)

        use(state, resolver, "Communio", 7.0)
        self.assertEqual(state.lemure_shroud, 0)
        self.assertGreater(state.perfectio_parata, 7.0)
        use(state, resolver, "Perfectio", 9.5)
        self.assertEqual(state.perfectio_parata, -1.0)
        self.assertEqual(state.get_resource_warnings(), [])

    def test_soul_and_executioner_update_on_press_confirm(self):
        resolver = SkillResolver("RPR", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = RprJobState()
        use(state, resolver, "Soul Slice", 0.0)
        self.assertEqual(state.soul, 50)
        use(state, resolver, "Blood Stalk", 0.5)
        self.assertEqual(state.soul, 0)
        self.assertEqual(state.soul_reaver, 1)

        state.soul = 50
        self.assertEqual(use(state, resolver, "Gluttony", 2.0), 560)
        self.assertEqual(state.executioner, 2)
        self.assertEqual(use(state, resolver, "Executioner's Gibbet", 3.0), 760)
        self.assertEqual(state.executioner, 1)
        self.assertEqual(use(state, resolver, "Executioner's Gallows", 5.5), 820)
        self.assertEqual(state.executioner, 0)

        state.soul = 0
        use(state, resolver, "+10 Soul Gauge", 8.0)
        self.assertEqual(state.soul, 10)
        self.assertEqual(state.get_resource_warnings(), [])

    def test_combo_soul_enhancements_and_ready_states_expire(self):
        resolver = SkillResolver("RPR", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = RprJobState()
        use(state, resolver, "Waxing Slice", 0.0)
        self.assertEqual(state.soul, 0)
        use(state, resolver, "Slice", 2.5)
        use(state, resolver, "Waxing Slice", 5.0)
        self.assertEqual(state.soul, 20)

        state.soul_reaver = 1
        state.soul_reaver_until = 30.0
        self.assertEqual(use(state, resolver, "Gibbet", 6.0), 560)
        use(state, resolver, "Slice", 8.5)
        state.soul_reaver = 1
        state.soul_reaver_until = 30.0
        self.assertEqual(use(state, resolver, "Gallows", 11.0), 620)

        state.soul_reaver = 1
        state.soul_reaver_until = 100.0
        state.enhanced_gibbet = 12.0
        self.assertEqual(use(state, resolver, "Gibbet", 13.0), 560)

        harpe = resolver.get("Harpe")
        state.enhanced_harpe_until = 20.0
        self.assertEqual(state.effective_cast_time("Harpe", harpe, {}, 14.0, 1.3), 0.0)
        self.assertEqual(
            state.effective_cast_time("Harpe", harpe, {"cast_time": 1.3}, 14.0, 1.3),
            1.3,
        )

        state.soul_reaver = 1
        state.soul_reaver_until = 15.0
        state.on_press("Gibbet", resolver.get("Gibbet"), 16.0, 16.0)
        use(state, resolver, "Arcane Circle", 20.0)
        state.on_press("Plentiful Harvest", resolver.get("Plentiful Harvest"), 51.0, 51.0)
        self.assertIn(
            "rpr_soul_reaver_missing",
            {warning["code"] for warning in state.get_resource_warnings()},
        )
        self.assertIn(
            "rpr_immortal_sacrifice_missing",
            {warning["code"] for warning in state.get_resource_warnings()},
        )

    def test_whorl_of_death_refreshes_all_hit_targets(self):
        resolver = SkillResolver("RPR", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = RprJobState()
        skill = resolver.get("Whorl of Death")
        state.on_damage_resolved(
            "Whorl of Death",
            skill,
            1.0,
            False,
            {"tid": 2, "targets": 3},
        )

        self.assertTrue(state.active_damage_buffs(1.1, target_id=1)["rpr_deaths_design"])
        self.assertTrue(state.active_damage_buffs(1.1, target_id=2)["rpr_deaths_design"])
        self.assertTrue(state.active_damage_buffs(1.1, target_id=3)["rpr_deaths_design"])


if __name__ == "__main__":
    unittest.main()
