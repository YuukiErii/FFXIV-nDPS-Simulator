import unittest

from src.ffxiv_ndps_simulator.jobs.smn import SmnJobState
from src.ffxiv_ndps_simulator.sim import DpsSimulator
from src.ffxiv_ndps_simulator.xiv_skill_provider import get_amas_provider


def skill(potency=0, is_gcd=True):
    return {"potency": potency, "base_potency": potency, "is_gcd": is_gcd}


def press(state, name, t, data=None):
    data = data or skill()
    payload = state.on_press(name, data, t, t)
    state.on_press_confirmed(name, data, t, payload)
    return payload


class SmnJobStateTests(unittest.TestCase):
    def test_pet_coefficient_falloff_and_demi_timing(self):
        state = SmnJobState()
        event = state.followup_damage_events(
            "Summon Ifrit II", skill(), 0.0, {"targets": 3}
        )[0]
        self.assertEqual(state.PET_DAMAGE_SCALAR, 0.8)
        self.assertEqual(event["potency"], 640)
        self.assertTrue(event["is_aoe"])
        self.assertEqual(event["decay"], 0.5)
        self.assertEqual(event["targets"], 3)
        self.assertTrue(event["snapshot_potion_now"])
        self.assertEqual(
            state.followup_damage_events("Enkindle Bahamut", skill(0, False), 0.0, {"targets": 2})[0]["potency"],
            1040,
        )
        autos = state.followup_damage_events("Summon Solar Bahamut", skill(), 0.0, {"targets": 3})
        self.assertEqual([x["potency"] for x in autos], [128] * 4)
        self.assertEqual([x["targets"] for x in autos], [1] * 4)
        self.assertTrue(all(x["snapshot_potion_at_followup"] for x in autos))
        self.assertAlmostEqual(0.76 + autos[0]["delay"], 3.163)

    def test_demi_cycle_arcanum_and_elemental_favors(self):
        state = SmnJobState()
        press(state, "Summon Solar Bahamut", 0.0)
        self.assertEqual(state.demi, "solar")
        self.assertTrue(all(state.arcanum.values()))
        self.assertGreater(state.refulgent_lux_until, 0)
        press(state, "Lux Solaris", 1.0, skill(0, False))
        self.assertLess(state.refulgent_lux_until, 0)

        press(state, "Summon Titan II", 16.0)
        self.assertEqual(state.gem_charges, 4)
        press(state, "Topaz Rite", 18.5, skill(340))
        self.assertEqual(state.gem_charges, 3)
        self.assertTrue(state.titan_favor)
        press(state, "Mountain Buster", 19.2, skill(160, False))
        self.assertEqual(state.gem_charges, 3)
        self.assertFalse(state.titan_favor)

        press(state, "Summon Bahamut", 60.0)
        self.assertEqual(state.demi, "bahamut")
        self.assertEqual(state.next_demi_index, 2)

    def test_ifrit_garuda_aetherflow_and_ready_actions(self):
        state = SmnJobState()
        press(state, "Summon Solar Bahamut", 0.0)
        press(state, "Summon Ifrit II", 16.0)
        press(state, "Crimson Cyclone", 18.5, skill(560))
        self.assertTrue(state.crimson_strike_ready)
        press(state, "Crimson Strike", 21.0, skill(560))
        self.assertFalse(state.crimson_strike_ready)

        press(state, "Summon Garuda II", 24.0)
        self.assertEqual(state.gem_charges, 4)
        press(state, "Slipstream", 26.5, skill(520))
        self.assertEqual(state.gem_charges, 4)
        self.assertFalse(state.garuda_favor)

        press(state, "Energy Drain", 30.0, skill(200, False))
        self.assertEqual(state.aetherflow, 2)
        press(state, "Necrotize", 30.7, skill(500, False))
        self.assertEqual(state.aetherflow, 1)
        press(state, "Ruin IV", 32.0, skill(520))
        self.assertLess(state.further_ruin_until, 0)
        press(state, "Searing Light", 34.0, skill(0, False))
        press(state, "Searing Flash", 34.7, skill(700, False))
        self.assertLess(state.searing_flash_until, 0)

    def test_swiftcast_makes_next_casted_spell_instant(self):
        state = SmnJobState()
        press(state, "Swiftcast", 0.0, skill(0, False))
        ruby = {"amas_name": "Ruby Rite", "cast": 2.8, "potency": 620, "is_gcd": True}

        self.assertEqual(state.effective_cast_time("Ruby Rite", ruby, {}, 1.0, 2.8), 0.0)
        state.on_press("Ruby Rite", ruby, 1.0, 1.0)
        self.assertEqual(state.swiftcast_until, -1.0)

    def test_7_5_provider_values_and_demi_source_delay(self):
        provider = get_amas_provider("7.5", 100)
        if provider is None:
            self.skipTest("AMAS provider unavailable")
        expected = {
            "Painflare": 220,
            "Ruby Rite": 620,
            "Crimson Cyclone": 560,
            "Crimson Strike": 560,
            "Necrotize": 500,
        }
        for name, potency in expected.items():
            self.assertEqual(provider.get("SMN", name)["potency"], potency)
        self.assertEqual(provider.get("SMN", "Summon Bahamut")["delay"], 0.76)
        self.assertEqual(provider.get("SMN", "Akh Morn")["potency"], 1040)
        self.assertIsNone(provider.get("SMN", "Akh Morn")["job_mod_override"])

    def test_pet_damage_uses_pet_snapshot_and_demi_autos_use_their_own_snapshot(self):
        stats = {
            "job": "SMN", "version": "7.5", "main_stat": 6498,
            "crt": 3605, "det": 2426, "dh": 1793, "sks": 689,
            "wd": 158, "delay": 3.12,
        }
        timeline = [
            (0.0, "Searing Light", 1),
            (17.0, "Summon Ifrit II", 1),
            (18.0, "Tincture", 1),
        ]
        *_, log, _targets, _snapshots, _custom, _warnings = DpsSimulator(
            stats, timeline, iterations=1
        ).run_one_simulation(is_first_run=True)
        inferno = next(row for row in log if row["name"] == "Inferno")
        self.assertGreater(inferno["time"], 20.0)
        self.assertIn("灼热", inferno["buffs"])
        self.assertIn("药", inferno["buffs"])

        demi_timeline = [(0.0, "Summon Solar Bahamut", 1), (1.0, "Tincture", 1)]
        *_, demi_log, _targets, _snapshots, _custom, _warnings = DpsSimulator(
            stats, demi_timeline, iterations=1
        ).run_one_simulation(is_first_run=True)
        first_luxwave = next(row for row in demi_log if row["name"] == "Luxwave")
        self.assertIn("药", first_luxwave["buffs"])


if __name__ == "__main__":
    unittest.main()
