import pathlib
import sys
import unittest


SIMULATOR_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from sim import DpsSimulator  # noqa: E402


class PartyBuffTimingTests(unittest.TestCase):
    def test_generic_party_buff_uses_start_and_until(self):
        sim = DpsSimulator(
            {
                "job": "RPR",
                "wd": 158,
                "main_stat": 6490,
                "crt": 3605,
                "det": 2527,
                "dh": 1961,
                "sks": 420,
            },
            [(0.0, "Arcane Circle", 1), (0.59, "Probe", 1), (0.60, "Probe", 1)],
            iterations=1,
        )
        skills = {
            "Arcane Circle": {
                "amas_name": "Arcane Circle",
                "cast": 0.0,
                "delay": 0.0,
                "potency": 0,
                "is_gcd": False,
                "buff": {
                    "key": "buff:Arcane Circle",
                    "name": "Arcane Circle",
                    "duration": 20.0,
                    "damage_mult": 1.03,
                },
            },
            "Probe": {
                "amas_name": "Probe",
                "cast": 0.0,
                "delay": 0.0,
                "potency": 100,
                "is_gcd": True,
            },
        }
        sim.get_skill = lambda name: dict(skills[name])

        _dps, _dur, _last_hit, stats, log = sim.run_batch()
        probe_rows = [row for row in log if row["name"] == "Probe"]

        self.assertEqual([row["buffs"] for row in probe_rows], ["-", "增伤"])
        self.assertEqual(
            [(row["effective_potency"], row["count"]) for row in stats["skill_variants"] if row["skill"] == "Probe"],
            [(100.0, 1), (103.0, 1)],
        )


if __name__ == "__main__":
    unittest.main()
