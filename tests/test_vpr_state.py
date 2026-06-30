import unittest

from src.ffxiv_ndps_simulator.jobs.vpr import VprJobState
from src.ffxiv_ndps_simulator.xiv_skill_provider import get_amas_provider


def skill(potency=0, is_gcd=True, aoe=False):
    return {"potency": potency, "base_potency": potency, "is_gcd": is_gcd, "is_aoe": aoe}


def use(state, name, t, data=None, immune=False):
    data = data or skill()
    payload = state.on_press(name, data, t, t)
    state.on_press_confirmed(name, data, t, payload)
    potency, is_combo = state.resolve_potency(name, data, t, payload)
    state.on_damage_resolved(name, data, t, is_combo, {**payload, "damage_immune": immune})
    return potency


class VprJobStateTests(unittest.TestCase):
    def test_honed_venom_combo_and_offering(self):
        state = VprJobState()
        self.assertEqual(use(state, "Steel Fangs", 0.0, skill(200)), 200)
        self.assertEqual(use(state, "Hunter's Sting", 2.5, skill(300)), 300)
        self.assertEqual(use(state, "Flanksting Strike", 5.0, skill(400)), 400)
        self.assertEqual(state.serpent_offering, 10)
        self.assertTrue(state.death_rattle_ready)
        use(state, "Death Rattle", 5.7, skill(280, False))
        use(state, "Reaving Fangs", 7.5, skill(200))
        use(state, "Hunter's Sting", 10.0, skill(300))
        self.assertEqual(use(state, "Hindsting Strike", 12.5, skill(400)), 500)
        self.assertEqual(use(state, "Steel Fangs", 15.0, skill(200)), 300)
        state.st_combo = "hunter"
        self.assertEqual(
            state.resolve_potency("Flanksting Strike", skill(400), 16.0, {"positional_hit": False})[0],
            340,
        )

    def test_ire_reawaken_generation_legacy_and_ouroboros(self):
        state = VprJobState()
        state.serpent_offering = 70
        use(state, "Serpent's Ire", 0.0, skill(0, False))
        self.assertEqual(state.serpent_offering, 70)
        use(state, "Reawaken", 1.0, skill(750, True, True))
        self.assertEqual(state.serpent_offering, 70)
        self.assertEqual(use(state, "First Generation", 3.0, skill(680, True, True)), 680)
        self.assertEqual(state.legacy_ready, 1)
        use(state, "First Legacy", 3.7, skill(320, False, True))
        self.assertEqual(use(state, "Second Generation", 5.0, skill(680, True, True)), 680)
        use(state, "Ouroboros", 7.0, skill(1150, True, True))
        self.assertEqual(state.reawaken_stacks, 0)
        self.assertEqual(state.legacy_ready, 0)

    def test_coil_den_and_uncoiled_followups_are_distinct(self):
        state = VprJobState()
        use(state, "Vicewinder", 0.0, skill(540))
        self.assertEqual(state.rattling_coils, 1)
        self.assertEqual(use(state, "Hunter's Coil", 3.0, skill(680)), 680)
        self.assertEqual(use(state, "Twinfang Bite", 3.7, skill(120, False)), 170)
        self.assertEqual(use(state, "Twinblood Bite", 4.4, skill(120, False)), 170)
        self.assertEqual(state.serpent_offering, 5)

        use(state, "Swiftskin's Coil", 5.0, skill(680))
        self.assertEqual(use(state, "Twinfang Bite", 5.7, {**skill(120, False), "base_potency": 170}), 120)
        self.assertEqual(use(state, "Twinblood Bite", 6.4, {**skill(120, False), "base_potency": 170}), 120)

        use(state, "Uncoiled Fury", 7.0, skill(680, True, True))
        self.assertEqual(use(state, "Uncoiled Twinfang", 7.7, skill(120, False, True)), 170)
        self.assertEqual(use(state, "Uncoiled Twinblood", 8.4, skill(120, False, True)), 170)
        self.assertEqual(state.rattling_coils, 0)

        use(state, "Vicepit", 10.0, skill(250, True, True))
        use(state, "Swiftskin's Den", 13.0, skill(300, True, True))
        self.assertEqual(use(state, "Twinblood Thresh", 13.7, skill(50, False, True)), 80)
        self.assertEqual(use(state, "Twinfang Thresh", 14.4, skill(50, False, True)), 80)

    def test_7_5_provider_overrides(self):
        provider = get_amas_provider("7.5", 100)
        if provider is None:
            self.skipTest("AMAS provider unavailable")
        self.assertEqual(provider.get("VPR", "Vicewinder")["potency"], 540)
        self.assertEqual(provider.get("VPR", "Hunter's Coil")["potency"], 680)
        self.assertEqual(provider.get("VPR", "Reawaken")["decay"], 0.75)
        self.assertEqual(provider.get("VPR", "First Legacy")["decay"], 0.75)


if __name__ == "__main__":
    unittest.main()
