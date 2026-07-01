import pathlib
import random
import sys
import types
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.blm import BlmJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver  # noqa: E402


BASE_STATS = {
    "job": "BLM",
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "party_bonus": 1.05,
    "version": "7.5",
}


class BlmJobStateTests(unittest.TestCase):
    def _use(self, state, name, current_time, skill=None):
        skill = skill or {"amas_name": name, "cast": 0, "potency": 0}
        state.on_press(name, skill, current_time, current_time)
        state.on_press_complete(name, current_time)

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

    def test_polyglot_ticks_while_elemental_state_is_maintained(self):
        state = BlmJobState()
        state.on_press("Fire 3", {"amas_name": "Fire III", "potency": 290}, 0.0, 0.0)
        state.on_press_complete("Fire 3", 0.0)

        state.on_press("Xenoglossy", {"amas_name": "Xenoglossy", "potency": 890}, 31.0, 31.0)
        state.on_press_complete("Xenoglossy", 31.0)

        self.assertEqual(state.polyglot, 0)
        self.assertFalse(state.get_resource_warnings())

    def test_astral_fire_does_not_expire_in_75(self):
        state = BlmJobState()
        state.on_press("Fire 3", {"amas_name": "Fire III", "potency": 290}, 0.0, 0.0)
        state.on_press_complete("Fire 3", 0.0)

        state.on_press("Fire IV", {"amas_name": "Fire IV", "potency": 300}, 120.0, 120.0)

        self.assertEqual(state.astral_fire, 3)
        self.assertNotIn("blm_astral_fire_missing", {
            warning["code"] for warning in state.get_resource_warnings()
        })

    def test_active_buff_lookup_does_not_advance_polyglot(self):
        state = BlmJobState()
        state.on_press("Fire 3", {"amas_name": "Fire III", "potency": 290}, 0.0, 0.0)
        state.on_press_complete("Fire 3", 0.0)

        state.active_damage_buffs(31.0)

        self.assertEqual(state.polyglot, 0)

    def test_expired_instant_cast_status_does_not_zero_later_cast(self):
        state = BlmJobState()
        state.on_press_complete("Swiftcast", 0.0)

        cast = state.effective_cast_time(
            "Fire IV",
            {"amas_name": "Fire IV", "cast": 2.0, "potency": 300},
            {},
            20.0,
            2.0,
        )

        self.assertEqual(cast, 2.0)

    def test_75_damage_table_matches_official_job_guide(self):
        expected = {
            "Fire": (180, 0, 0.0, False, 0.0, 2.0),
            "Blizzard": (180, 0, 0.0, False, 0.0, 2.0),
            "Scathe": (120, 0, 0.0, False, 0.0, 0.0),
            "Fire III": (290, 0, 0.0, False, 0.0, 3.5),
            "Blizzard III": (290, 0, 0.0, False, 0.0, 3.5),
            "Freeze": (120, 0, 0.0, True, 0.0, 2.0),
            "Thunder III": (120, 50, 27.0, False, 0.0, 0.0),
            "Flare": (240, 0, 0.0, True, 0.3, 2.0),
            "Blizzard IV": (300, 0, 0.0, False, 0.0, 2.0),
            "Fire IV": (300, 0, 0.0, False, 0.0, 2.0),
            "Thunder IV": (80, 35, 21.0, True, 0.0, 0.0),
            "Foul": (600, 0, 0.0, True, 0.25, 0.0),
            "Despair": (350, 0, 0.0, False, 0.0, 0.0),
            "Xenoglossy": (890, 0, 0.0, False, 0.0, 0.0),
            "High Fire II": (100, 0, 0.0, True, 0.0, 3.0),
            "High Blizzard II": (100, 0, 0.0, True, 0.0, 3.0),
            "Paradox": (540, 0, 0.0, False, 0.0, 0.0),
            "High Thunder": (150, 60, 30.0, False, 0.0, 0.0),
            "High Thunder II": (100, 40, 24.0, True, 0.0, 0.0),
            "Flare Star": (500, 0, 0.0, True, 0.65, 2.0),
        }
        resolver = SkillResolver("BLM", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        for name, values in expected.items():
            with self.subTest(name=name):
                skill = resolver.get(name)
                actual = (
                    skill["potency"],
                    skill.get("dot_potency", 0),
                    skill.get("dot_duration", 0.0),
                    skill["is_aoe"],
                    skill["decay"],
                    skill["cast"],
                )
                self.assertEqual(actual, values)

    def test_high_thunder_ii_splits_multi_boss_dots_per_target(self):
        state = BlmJobState()
        skill = {
            "amas_name": "High Thunder II",
            "dot_name": "High Thunder II",
            "dot_potency": 40,
            "dot_duration": 24.0,
            "dot_primary_only": False,
        }
        state.set_event_context({"multi_boss_mode": True, "target_ids": [1, 2]})

        dots = state.dot_applications("High Thunder II", skill, 0.5, 2, 1, {}, False)

        self.assertEqual([dot["tid"] for dot in dots], [1, 2])
        self.assertEqual([dot["targets"] for dot in dots], [1, 1])

    def test_target_txt_ids_keep_single_target_thunder_dots_without_multi_mode(self):
        skills = {
            "High Thunder": {
                "amas_name": "High Thunder",
                "cast": 0,
                "delay": 0.5,
                "potency": 150,
                "base_potency": 150,
                "dot_potency": 60,
                "dot_duration": 30.0,
                "dot_primary_only": True,
                "is_aoe": False,
                "decay": 0,
                "combo_prev": [],
            },
            "Scathe": {
                "amas_name": "Scathe",
                "cast": 0,
                "delay": 0.5,
                "potency": 1,
                "base_potency": 1,
                "is_aoe": False,
                "decay": 0,
                "combo_prev": [],
            },
        }
        timeline = [
            {"time": 0.0, "name": "High Thunder", "targets": 1, "target_ids": [1]},
            {"time": 3.0, "name": "High Thunder", "targets": 1, "target_ids": [2]},
            {"time": 35.0, "name": "Scathe", "targets": 1},
        ]
        sim = DpsSimulator(dict(BASE_STATS), timeline, iterations=1)
        sim.get_skill = types.MethodType(lambda self, name: skills.get(name), sim)

        random.seed(1)
        result = sim.run_one_simulation(is_first_run=True)

        self.assertEqual(result[9]["High Thunder"], 22)
        self.assertIn("DoT(T2)", {row["targets"] for row in result[8]})
        details = sim.last_dot_details
        self.assertEqual(len(details), 2)
        self.assertEqual({row["target_id"] for row in details}, {1, 2})
        self.assertEqual(sum(row["ticks"] for row in details), 20)
        self.assertEqual(sum(row["missed_ticks"] for row in details), 0)
        self.assertTrue(all(row["damage"] > 0 for row in details))

    def test_high_thunder_ii_dot_ticks_respect_secondary_target_downtime(self):
        skills = {
            "Blizzard III": {
                "amas_name": "Blizzard III",
                "cast": 0,
                "delay": 0,
                "potency": 0,
                "base_potency": 0,
                "is_aoe": False,
                "decay": 0,
                "combo_prev": [],
            },
            "High Thunder II": {
                "amas_name": "High Thunder II",
                "cast": 0,
                "delay": 0.5,
                "potency": 100,
                "base_potency": 100,
                "dot_potency": 40,
                "dot_duration": 24.0,
                "dot_primary_only": False,
                "is_aoe": True,
                "decay": 0,
                "combo_prev": [],
            },
            "Scathe": {
                "amas_name": "Scathe",
                "cast": 0,
                "delay": 0.5,
                "potency": 1,
                "base_potency": 1,
                "is_aoe": False,
                "decay": 0,
                "combo_prev": [],
            },
        }
        timeline = [
            (-4.0, "Blizzard III", 1),
            (0.0, "High Thunder II", 2, {"target_ids": [1, 2]}),
            (35.0, "Scathe", 1),
        ]
        sim = DpsSimulator(
            dict(BASE_STATS),
            timeline,
            downtime_config={2: [(0.6, 30.0)]},
            multi_boss_mode=True,
            iterations=1,
        )
        sim.get_skill = types.MethodType(lambda self, name: skills.get(name), sim)

        random.seed(1)
        result = sim.run_one_simulation(is_first_run=False)

        self.assertEqual(result[9]["High Thunder II"], 10)

    def test_default_casts_use_spell_speed_and_ley_lines(self):
        sim = DpsSimulator(dict(BASE_STATS), [], iterations=1)
        fire4 = sim.get_skill("Fire IV")
        fire3 = sim.get_skill("Fire III")
        blizzard3 = sim.get_skill("Blizzard III")
        if fire4 is None or fire3 is None or blizzard3 is None:
            self.skipTest("AMAS skill provider is unavailable")

        speed_cast = sim.effective_cast_time(fire4, {})
        self.assertEqual(speed_cast, 1.97)

        state = BlmJobState()
        state.ley_lines_until = 10.0
        self.assertAlmostEqual(
            state.effective_cast_time("Fire IV", fire4, {}, 1.0, speed_cast),
            1.6745,
        )
        state = BlmJobState()
        state.umbral_ice = 3
        self.assertEqual(sim.effective_cast_time(fire3, {}), 3.45)
        self.assertAlmostEqual(
            state.effective_cast_time("Fire III", fire3, {}, 1.0, 3.45),
            1.725,
        )
        state.ley_lines_until = 10.0
        self.assertAlmostEqual(
            state.effective_cast_time("Fire III", fire3, {}, 1.0, 3.45),
            1.46625,
        )
        state = BlmJobState()
        state.astral_fire = 3
        self.assertAlmostEqual(
            state.effective_cast_time(
                "Blizzard III",
                blizzard3,
                {},
                1.0,
                sim.effective_cast_time(blizzard3, {}),
            ),
            1.725,
        )
        self.assertEqual(sim.effective_cast_time(fire4, {"cast_time": 2.0}), 2.0)

    def test_firestarter_freeze_and_astral_soul_effects(self):
        state = BlmJobState()
        self._use(state, "Fire III", 0.0, {"amas_name": "Fire III", "cast": 3.5, "potency": 290})
        self._use(state, "Fire IV", 3.0, {"amas_name": "Fire IV", "cast": 2.0, "potency": 300})
        self.assertEqual(state.astral_soul, 1)
        self._use(state, "Despair", 6.0, {"amas_name": "Despair", "cast": 0.0, "potency": 350})
        self.assertEqual(state.astral_soul, 1)

        self._use(state, "Paradox", 9.0, {"amas_name": "Paradox", "cast": 0.0, "potency": 540})
        self.assertEqual(state.firestarter, 1)
        fire3 = {"amas_name": "Fire III", "cast": 3.5, "potency": 290}
        self.assertEqual(state.effective_cast_time("Fire III", fire3, {}, 10.0, 3.5), 0.0)
        self._use(state, "Fire III", 10.0, fire3)
        self.assertEqual(state.firestarter, 0)

        ice = BlmJobState()
        self._use(ice, "Blizzard III", 0.0, {"amas_name": "Blizzard III", "cast": 3.5, "potency": 290})
        self._use(ice, "Freeze", 3.0, {"amas_name": "Freeze", "cast": 2.0, "potency": 120})
        self.assertEqual(ice.umbral_hearts, 3)

    def test_mp_and_umbral_hearts_follow_75_rules(self):
        state = BlmJobState()
        fire3 = {"amas_name": "Fire III", "cast": 3.5, "potency": 290}
        fire4 = {"amas_name": "Fire IV", "cast": 2.0, "potency": 300}

        self._use(state, "Fire III", 0.0, fire3)
        self.assertEqual(state.mp, 8000)

        self._use(state, "Fire IV", 3.0, fire4)
        self.assertEqual(state.mp, 6400)

        state.umbral_hearts = 3
        self._use(state, "Fire IV", 6.0, fire4)
        self.assertEqual(state.mp, 5600)
        self.assertEqual(state.umbral_hearts, 2)

        self._use(state, "Despair", 9.0, {"amas_name": "Despair", "cast": 0.0, "potency": 350})
        self.assertEqual(state.mp, 0)

        self._use(state, "Blizzard III", 12.0, {"amas_name": "Blizzard III", "cast": 3.5, "potency": 290})
        self.assertEqual(state.mp, 10000)
        self.assertEqual(state.umbral_ice, 3)

        self._use(state, "Fire III", 15.0, fire3)
        self.assertEqual(state.mp, 10000)
        self.assertEqual(state.astral_fire, 3)

        state.paradox = 1
        self._use(state, "Paradox", 18.0, {"amas_name": "Paradox", "cast": 0.0, "potency": 540})
        self.assertEqual(state.mp, 8400)
        self.assertEqual(state.firestarter, 1)

        transpose = BlmJobState()
        transpose.mp = 1000
        transpose.astral_fire = 1
        transpose._refresh_enochian(0.0)
        self._use(transpose, "Transpose", 1.0, {"amas_name": "Transpose", "cast": 0.0, "potency": 0})
        self.assertEqual(transpose.mp, 1000)
        self.assertEqual(transpose.umbral_ice, 1)

        flare = BlmJobState()
        flare.mp = 10000
        flare.astral_fire = 3
        flare.umbral_hearts = 3
        flare._refresh_enochian(0.0)
        self._use(flare, "Flare", 1.0, {"amas_name": "Flare", "cast": 2.0, "potency": 240})
        self.assertEqual(flare.mp, 3333)
        self.assertEqual(flare.umbral_hearts, 0)

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
