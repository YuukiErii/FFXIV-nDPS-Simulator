import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.blm import BlmJobState  # noqa: E402
from sim import SkillResolver  # noqa: E402


class BlmJobStateTests(unittest.TestCase):
    def test_astral_fire_and_enochian_apply_to_fire_spell(self):
        state = BlmJobState()
        state.on_press("Fire 3", {"amas_name": "Fire III", "potency": 290}, 0.0, 0.0)
        state.on_press_complete("Fire 3", 0.0)

        self.assertEqual(state.astral_fire, 3)
        self.assertAlmostEqual(state.active_damage_buffs(0.1)["damage_mult"], 1.27)
        potency, _ = state.resolve_potency("Fire 4", {"amas_name": "Fire IV", "potency": 300}, 0.1, {})
        self.assertAlmostEqual(potency, 540.0)

    def test_transpose_switches_aspect_without_applying_cast_speed(self):
        state = BlmJobState()
        state.on_press("Fire 3", {"amas_name": "Fire III", "potency": 290}, 0.0, 0.0)
        state.on_press_complete("Fire 3", 0.0)
        state.on_press("Transpose", {"amas_name": "Transpose", "potency": 0}, 2.5, 2.5)
        state.on_press_complete("Transpose", 2.5)

        self.assertEqual(state.astral_fire, 0)
        self.assertEqual(state.umbral_ice, 1)
        self.assertAlmostEqual(state.active_damage_buffs(2.6)["damage_mult"], 1.27)
        potency, _ = state.resolve_potency("Fire 4", {"amas_name": "Fire IV", "potency": 300}, 2.6, {})
        self.assertAlmostEqual(potency, 270.0)

    def test_sample_blm_skills_are_not_marked_as_state_gaps(self):
        resolver = SkillResolver("BLM")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        for name in [
            "Fire 3", "Fire 4", "High Thunder", "High Thunder 2",
            "Amplifier", "Ley Lines", "Despair", "Manafont",
            "Flare Star", "Paradox", "Swiftcast", "Triplecast",
            "Flare", "Transpose", "Blizzard 3", "Blizzard 4",
            "Xenoglossy", "Umbral Soul",
        ]:
            with self.subTest(name=name):
                cls = resolver.classify_skill(name)
                self.assertTrue(cls["known"])
                self.assertFalse(cls["needs_state"])
                self.assertFalse(cls["followup_unmodeled"])

    def test_generic_zero_damage_skills_are_runnable_for_blm(self):
        resolver = SkillResolver("BLM")
        for name in ["Tincture", "Surecast", "Lucid Dreaming"]:
            with self.subTest(name=name):
                skill = resolver.get(name)
                self.assertIsNotNone(skill)
                self.assertEqual(skill["potency"], 0)


if __name__ == "__main__":
    unittest.main()
