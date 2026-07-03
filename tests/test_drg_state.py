import pathlib
import sys
import unittest


SIMULATOR_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.drg import DrgJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver  # noqa: E402


def skill(name, potency=0, is_gcd=False):
    return {"amas_name": name, "potency": potency, "is_gcd": is_gcd}


def use(state, name, time=0.0, potency=0, is_gcd=False, is_combo=False):
    action = skill(name, potency, is_gcd)
    press = state.on_press(name, action, time, time)
    payload = {
        "source_roll_available": potency > 0,
        "is_gcd": is_gcd,
        **press,
    }
    state.on_press_confirmed(name, action, time, payload)
    state.on_damage_resolved(name, action, time, is_combo, payload)
    return press


class DrgJobStateTests(unittest.TestCase):
    def test_draconian_fire_feeds_firstminds_focus(self):
        state = DrgJobState()

        use(state, "Drakesbane", 0.0, 460, is_gcd=True, is_combo=True)
        self.assertGreater(state.draconian_fire_until, 0.0)
        self.assertEqual(state.firstminds_focus, 0)

        use(state, "Raiden Thrust", 2.5, 320, is_gcd=True)
        self.assertLess(state.draconian_fire_until, 0.0)
        self.assertEqual(state.firstminds_focus, 1)

        use(state, "Coerthan Torment", 5.0, 150, is_gcd=True, is_combo=True)
        use(state, "Draconian Fury", 7.5, 130, is_gcd=True)
        self.assertEqual(state.firstminds_focus, 2)

        state.on_press("Wyrmwind Thrust", skill("Wyrmwind Thrust", 440), 8.0, 8.0)
        use(state, "Wyrmwind Thrust", 8.0, 440)
        self.assertEqual(state.firstminds_focus, 0)
        self.assertNotIn("drg_firstminds_low", {w["code"] for w in state.get_resource_warnings()})

    def test_ready_windows_are_tracked(self):
        state = DrgJobState()

        state.on_press("Mirage Dive", skill("Mirage Dive", 380), 0.0, 0.0)
        self.assertIn("drg_dive_ready_missing", {w["code"] for w in state.get_resource_warnings()})
        state.resource_warnings = []
        use(state, "High Jump", 1.0, 400)
        use(state, "Mirage Dive", 2.0, 380)
        self.assertLess(state.dive_ready_until, 0.0)
        self.assertFalse(state.get_resource_warnings())

        state.on_press("Rise of the Dragon", skill("Rise of the Dragon", 550), 3.0, 3.0)
        self.assertIn("drg_dragons_flight_not_ready", {w["code"] for w in state.get_resource_warnings()})
        state.resource_warnings = []
        use(state, "Dragonfire Dive", 4.0, 500)
        use(state, "Rise of the Dragon", 5.0, 550)
        self.assertLess(state.dragons_flight_until, 0.0)
        self.assertFalse(state.get_resource_warnings())

        state.on_press("Starcross", skill("Starcross", 1000), 6.0, 6.0)
        self.assertIn("drg_starcross_not_ready", {w["code"] for w in state.get_resource_warnings()})
        state.resource_warnings = []
        use(state, "Geirskogul", 7.0, 280)
        use(state, "Stardiver", 8.0, 840)
        use(state, "Starcross", 9.0, 1000)
        self.assertLess(state.starcross_ready_until, 0.0)
        self.assertFalse(state.get_resource_warnings())

    def test_life_of_the_dragon_is_not_double_counted(self):
        state = DrgJobState()
        use(state, "Geirskogul", 0.0, 280)

        sim = DpsSimulator(
            {
                "job": "DRG",
                "wd": 158,
                "main_stat": 6490,
                "crt": 3605,
                "det": 2527,
                "dh": 1961,
                "sks": 420,
            },
            [(0.0, "Geirskogul", 1), (1.0, "Nastrond", 1)],
            iterations=1,
        )
        buffs = sim.get_active_damage_buffs(
            {
                "buff:Life of the Dragon": {
                    "name": "Life of the Dragon",
                    "until": 20.0,
                    "damage_mult": 1.15,
                }
            },
            1.0,
            job_state=state,
        )

        self.assertAlmostEqual(buffs["damage_mult"], 1.15)
        self.assertEqual(
            [factor for _label, factor in buffs["damage_factors"]].count(1.15),
            1,
        )
        self.assertTrue(buffs["drg_life"])

    def test_life_surge_targets_next_damage_gcd(self):
        state = DrgJobState()
        use(state, "Life Surge", 0.0)

        self.assertEqual(state.on_press("High Jump", skill("High Jump", 400), 1.0, 1.0), {})
        self.assertTrue(state.life_surge_ready)
        self.assertEqual(
            state.on_press("Piercing Talon", skill("Piercing Talon", 150, is_gcd=True), 2.0, 2.0),
            {"guaranteed_crit": True},
        )
        self.assertFalse(state.life_surge_ready)

    def test_self_and_party_buff_start_times_are_separate(self):
        state = DrgJobState()
        use(state, "Lance Charge", 10.0)
        self.assertTrue(state.active_damage_buffs(10.0)["drg_lance_charge"])

        use(state, "Battle Litany", 20.0)
        self.assertFalse(state.active_damage_buffs(20.61)["drg_battle_litany"])
        self.assertTrue(state.active_damage_buffs(20.62)["drg_battle_litany"])
        self.assertTrue(state.active_damage_buffs(40.61)["drg_battle_litany"])
        self.assertFalse(state.active_damage_buffs(40.62)["drg_battle_litany"])

    def test_starcross_uses_75_potency(self):
        resolver = SkillResolver("DRG", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")
        self.assertEqual(resolver.get("Starcross")["potency"], 1000)


if __name__ == "__main__":
    unittest.main()
