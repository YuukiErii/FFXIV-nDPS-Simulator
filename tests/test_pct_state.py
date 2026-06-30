import pathlib
import random
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.pct import PctJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver, normalize_skill_name_for_job  # noqa: E402
from xiv_axis_csv import parse_axis_csv  # noqa: E402


BASE_STATS = {
    "job": "PCT",
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "party_bonus": 1.05,
    "version": "7.5",
}


class PctJobStateTests(unittest.TestCase):
    def _use(self, state, name, current_time):
        state.on_press(name, {"amas_name": name, "potency": 0}, current_time, current_time)
        state.on_press_confirmed(name, {"amas_name": name, "potency": 0}, current_time, {})

    def test_pct_fru_prepull_opener_has_tracked_resources(self):
        state = PctJobState()
        for t, name in [
            (-4.7, "Rainbow Drip"),
            (0.0, "Striking Muse"),
            (0.5, "Pom Muse"),
            (1.2, "Wing Motif"),
            (4.3, "Starry Muse"),
            (5.2, "Hammer Stamp"),
            (5.8, "Subtractive Palette"),
            (7.7, "Blizzard in Cyan"),
            (10.2, "Stone in Yellow"),
            (12.7, "Thunder in Magenta"),
            (15.2, "Comet in Black"),
            (15.7, "Winged Muse"),
            (16.3, "Mog of the Ages"),
        ]:
            self._use(state, name, t)

        self.assertFalse(state.get_resource_warnings())

    def test_pct_fru_representative_axes_have_no_resource_warnings(self):
        for relative in [
            "examples/skill_lines/pct_fru/23_desaturation.csv",
            "examples/skill_lines/pct_fru/23_desaturation_p4_fast.csv",
        ]:
            with self.subTest(relative=relative):
                events, _ = parse_axis_csv(
                    REPO_ROOT / relative,
                    normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, "PCT"),
                )
                sim = DpsSimulator(dict(BASE_STATS), events, iterations=1)
                random.seed(1)
                warnings = sim.run_one_simulation(is_first_run=True)[-1]
                self.assertEqual(warnings, [])

    def test_pct_missing_motif_still_warns(self):
        state = PctJobState()
        self._use(state, "Fanged Muse", 1.0)

        codes = [warning["code"] for warning in state.get_resource_warnings()]
        self.assertIn("pct_creature_motif_missing", codes)

    def test_blizzard_in_cyan_is_single_target(self):
        resolver = SkillResolver("PCT", "7.5")
        skill = resolver.get("Blizzard in Cyan")

        self.assertIsNotNone(skill)
        self.assertFalse(skill["is_aoe"])
        self.assertTrue(resolver.get("Blizzard II in Cyan")["is_aoe"])

    def test_75_damage_table_matches_official_job_guide(self):
        expected = {
            "Fire in Red": (490, False, 0.0), "Aero in Green": (530, False, 0.0),
            "Water in Blue": (570, False, 0.0), "Fire II in Red": (180, True, 0.0),
            "Aero II in Green": (200, True, 0.0), "Water II in Blue": (220, True, 0.0),
            "Pom Muse": (800, True, 0.7), "Winged Muse": (800, True, 0.7),
            "Clawed Muse": (800, True, 0.7), "Fanged Muse": (800, True, 0.7),
            "Mog of the Ages": (1000, True, 0.7),
            "Retribution of the Madeen": (1100, True, 0.7),
            "Hammer Stamp": (560, True, 0.7), "Hammer Brush": (580, True, 0.7),
            "Polishing Hammer": (600, True, 0.7), "Blizzard in Cyan": (860, False, 0.0),
            "Stone in Yellow": (900, False, 0.0), "Thunder in Magenta": (940, False, 0.0),
            "Blizzard II in Cyan": (360, True, 0.0), "Stone II in Yellow": (380, True, 0.0),
            "Thunder II in Magenta": (400, True, 0.0), "Holy in White": (570, True, 0.65),
            "Comet in Black": (940, True, 0.65), "Rainbow Drip": (1000, True, 0.85),
            "Star Prism": (1100, True, 0.7),
        }
        resolver = SkillResolver("PCT", "7.5")
        for name, values in expected.items():
            with self.subTest(name=name):
                skill = resolver.get(name)
                self.assertEqual((skill["potency"], skill["is_aoe"], skill["decay"]), values)
        for name in ["Hammer Stamp", "Hammer Brush", "Polishing Hammer"]:
            skill = resolver.get(name)
            self.assertTrue(skill["guaranteed_crit"] and skill["guaranteed_dh"])

    def test_rainbow_drip_uses_default_conditional_timing(self):
        skill = SkillResolver("PCT", "7.5").get("Rainbow Drip")

        self.assertEqual(skill["cast"], 4.0)
        self.assertEqual(skill["delay"], 1.24)

    def test_subtractive_palette_only_converts_existing_white_paint(self):
        state = PctJobState()
        state.subtractive_spectrum_until = 30.0
        self._use(state, "Subtractive Palette", 1.0)

        self.assertEqual(state.black_paint, 0)
        self.assertNotIn("pct_white_paint_low", {
            warning["code"] for warning in state.get_resource_warnings()
        })

    def test_hyperphantasia_and_starstruck_follow_their_windows(self):
        state = PctJobState()
        self._use(state, "Starry Muse", 0.0)
        self._use(state, "Star Prism", 1.0)
        self._use(state, "Star Prism", 2.0)
        self.assertIn("pct_starstruck_missing", {
            warning["code"] for warning in state.get_resource_warnings()
        })

        outside_field = PctJobState()
        self._use(outside_field, "Starry Muse", 0.0)
        self._use(outside_field, "Fire in Red", 21.0)
        self.assertEqual(outside_field.hyperphantasia, 5)

    def test_inspiration_and_swiftcast_adjust_implicit_cast_times(self):
        resolver = SkillResolver("PCT", "7.5")
        fire = resolver.get("Fire in Red")
        state = PctJobState()
        self._use(state, "Starry Muse", 0.0)
        self.assertEqual(state.effective_cast_time("Fire in Red", fire, {}, 1.0, 1.5), 1.125)

        state.hyperphantasia = 0
        self._use(state, "Swiftcast", 2.0)
        self.assertEqual(state.effective_cast_time("Fire in Red", fire, {}, 3.0, 1.5), 0.0)

    def test_default_casts_use_spell_speed_before_inspiration(self):
        resolver = SkillResolver("PCT", "7.5")
        fire = resolver.get("Fire in Red")
        sim = DpsSimulator(dict(BASE_STATS), [], iterations=1)

        speed_cast = sim.effective_cast_time(fire, {})
        self.assertEqual(speed_cast, 1.48)

        state = PctJobState()
        self._use(state, "Starry Muse", 0.0)
        self.assertAlmostEqual(
            state.effective_cast_time("Fire in Red", fire, {}, 1.0, speed_cast),
            1.11,
        )
        self.assertEqual(sim.effective_cast_time(fire, {"cast_time": 1.5}), 1.5)


if __name__ == "__main__":
    unittest.main()
