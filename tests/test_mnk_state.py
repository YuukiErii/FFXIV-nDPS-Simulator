import pathlib
import sys
import unittest


SIMULATOR_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.mnk import MnkJobState  # noqa: E402
from sim import DpsSimulator  # noqa: E402


def skill(name, potency=0):
    return {
        "amas_name": name,
        "potency": potency,
        "is_gcd": name in MnkJobState.WEAPONSKILLS,
    }


def use(state, name, potency=0, current_time=0.0, crits=0):
    action = skill(name, potency)
    press_state = state.on_press(name, action, current_time, current_time)
    override = state.consume_combo_override(name, action, current_time)
    payload = {
        "meikyo": override,
        "source_roll_available": potency > 0,
        "source_crit": crits > 0,
        "source_crit_count": crits,
        "is_gcd": action["is_gcd"],
        **press_state,
    }
    resolved, is_combo = state.resolve_potency(name, action, current_time, payload)
    payload["source_roll_available"] = resolved > 0
    state.on_damage_resolved(name, action, current_time, is_combo, payload)
    return resolved, payload


class MnkJobStateTests(unittest.TestCase):
    def test_fury_form_bonus_and_positionals(self):
        state = MnkJobState()
        state.form = "opo"
        state.form_until = 30.0

        self.assertEqual(use(state, "Dragon Kick", 320, 0.0)[0], 320)
        self.assertEqual(state.fury["opo"], 1)
        state.formless_until = 30.0
        potency, payload = use(state, "Leaping Opo", 260, 1.0, crits=1)

        self.assertEqual(potency, 460)
        self.assertTrue(payload["guaranteed_crit"])
        self.assertEqual(state.fury["opo"], 0)

    def test_perfect_balance_builds_beast_chakra_and_nadi(self):
        state = MnkJobState()
        use(state, "Perfect Balance", current_time=0.0)
        self.assertFalse(state.consume_combo_override("Brotherhood", skill("Brotherhood"), 0.1))
        self.assertEqual(state.perfect_balance_stacks, 3)

        use(state, "Dragon Kick", 320, 1.0)
        use(state, "Leaping Opo", 260, 2.0)
        use(state, "Dragon Kick", 320, 3.0)
        self.assertEqual(state._expected_blitz(), "Elixir Burst")
        self.assertEqual(use(state, "Masterful Blitz", 1500, 4.0)[0], 900)
        self.assertTrue(state.lunar_nadi)

        use(state, "Perfect Balance", current_time=5.0)
        use(state, "Dragon Kick", 320, 6.0)
        use(state, "Twin Snakes", 420, 7.0)
        use(state, "Demolish", 420, 8.0)
        self.assertEqual(state._expected_blitz(), "Rising Phoenix")
        self.assertEqual(use(state, "Masterful Blitz", 1500, 9.0)[0], 900)
        self.assertTrue(state.solar_nadi)

        use(state, "Perfect Balance", current_time=10.0)
        use(state, "Dragon Kick", 320, 11.0)
        use(state, "Dragon Kick", 320, 12.0)
        use(state, "Dragon Kick", 320, 13.0)
        self.assertEqual(state._expected_blitz(), "Phantom Rush")
        self.assertEqual(use(state, "Masterful Blitz", 1500, 14.0)[0], 1500)
        self.assertFalse(state.lunar_nadi)
        self.assertFalse(state.solar_nadi)

    def test_celestial_revolution_and_invalid_masterful_blitz(self):
        state = MnkJobState()
        self.assertEqual(use(state, "Masterful Blitz", 1500, 0.0)[0], 0)

        use(state, "Perfect Balance", current_time=1.0)
        use(state, "Dragon Kick", 320, 2.0)
        use(state, "Dragon Kick", 320, 3.0)
        use(state, "Twin Snakes", 420, 4.0)
        self.assertEqual(state._expected_blitz(), "Celestial Revolution")
        self.assertEqual(use(state, "Masterful Blitz", 1500, 5.0)[0], 600)
        self.assertTrue(state.lunar_nadi)

    def test_chakra_generation_spend_and_six_sided_star(self):
        state = MnkJobState()
        state.brotherhood_until = 30.0
        use(state, "Dragon Kick", 320, 1.0, crits=2)
        self.assertEqual(state.chakra, 3)

        state.chakra = 6
        potency, _ = use(state, "Six-sided Star", 1180, 2.0, crits=1)
        self.assertEqual(potency, 1260)
        self.assertEqual(state.chakra, 1)

        state.chakra = 10
        use(state, "The Forbidden Chakra", 400, 3.0)
        self.assertEqual(state.chakra, 5)

    def test_brotherhood_teammate_chakra_is_averaged(self):
        state = MnkJobState()
        use(state, "Brotherhood", current_time=0.0)

        state.on_press("Dragon Kick", skill("Dragon Kick", 320), 0.39, 0.39)
        self.assertEqual(state.chakra, 0)
        state.on_press("Dragon Kick", skill("Dragon Kick", 320), 0.40, 0.40)
        self.assertEqual(state.chakra, 1)
        state.on_press("Dragon Kick", skill("Dragon Kick", 320), 2.00, 2.00)
        self.assertEqual(state.chakra, 5)

        state.on_press("Dragon Kick", skill("Dragon Kick", 320), 4.00, 4.00)
        self.assertEqual(state.chakra, 10)
        use(state, "The Forbidden Chakra", 400, 4.1)
        self.assertEqual(state.chakra, 5)

    def test_replies_and_auto_attack_haste(self):
        state = MnkJobState()
        use(state, "Riddle of Fire", current_time=0.0)
        use(state, "Riddle of Wind", current_time=0.1)
        self.assertAlmostEqual(state.auto_attack_interval_multiplier(1.0), 0.4)

        use(state, "Wind's Reply", 1040, 1.0)
        use(state, "Fire's Reply", 1400, 2.0)
        self.assertLess(state.wind_rumination_until, 0)
        self.assertLess(state.fire_rumination_until, 0)
        self.assertGreater(state.formless_until, 2.0)
        self.assertAlmostEqual(state.auto_attack_interval_multiplier(16.0), 0.8)

    def test_prepull_attack_starts_auto_attacks_at_pull(self):
        stats = {
            "job": "MNK", "main_stat": 6490, "crt": 3605, "det": 2527,
            "dh": 1961, "sks": 420, "wd": 158, "party_bonus": 1.05,
        }
        sim = DpsSimulator(
            stats,
            [(-2.0, "Perfect Balance", 1), (-1.0, "Dragon Kick", 1), (5.0, "Dragon Kick", 1)],
            iterations=1,
        )
        skills = {
            "Perfect Balance": skill("Perfect Balance"),
            "Dragon Kick": skill("Dragon Kick", 320),
        }
        sim.get_skill = lambda name: dict(skills[name])

        result = sim.run_one_simulation(is_first_run=True)
        auto_rows = [row for row in result[8] if row["name"] == "Auto Attack"]

        self.assertEqual(result[3]["Auto Attack"], 3)
        self.assertAlmostEqual(auto_rows[0]["time"], 0.53)


if __name__ == "__main__":
    unittest.main()
