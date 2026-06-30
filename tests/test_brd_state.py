import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.brd import BrdJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver, normalize_skill_name_for_job  # noqa: E402
from xiv_axis_csv import parse_axis_csv  # noqa: E402


BASE_STATS = {
    "job": "BRD",
    "main_stat": 5925,
    "crt": 3378,
    "det": 2370,
    "dh": 1981,
    "sks": 420,
    "wd": 152,
    "delay": 3.04,
}


class BrdJobStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = SkillResolver("BRD", "7.5")
        if cls.resolver.provider is None:
            raise unittest.SkipTest("AMAS skill provider is unavailable")

    def use(self, state, name, t=0.0, payload_extra=None):
        skill = self.resolver.get(name)
        payload = {"is_gcd": skill.get("is_gcd"), "targets": 1, **(payload_extra or {})}
        state.set_event_context(payload)
        payload.update(state.on_press(name, skill, t, t))
        state.on_press_confirmed(name, skill, t, payload)
        potency, is_combo = state.resolve_potency(name, skill, t, payload)
        dots = state.dot_applications(
            name, skill, t, 1, 1, state.active_damage_buffs(t), False
        )
        state.on_damage_resolved(name, skill, t, is_combo, payload)
        followups = state.followup_damage_events(name, skill, t, payload)
        return payload, potency, dots, followups

    def test_song_buffs_coda_radiant_and_encore(self):
        state = BrdJobState()

        self.use(state, "The Wanderer's Minuet", 0.0)
        self.assertEqual(state.coda, {"wanderer"})
        self.assertAlmostEqual(state.active_damage_buffs(1.0)["crit_rate_add"], 0.02)

        self.use(state, "Radiant Finale", 1.0)
        self.assertEqual(state.coda, set())
        self.assertAlmostEqual(state.active_damage_buffs(2.0)["damage_mult"], 1.02)
        self.assertEqual(self.use(state, "Radiant Encore", 2.0)[1], 700)

        for t, song in [
            (45.0, "Mage's Ballad"),
            (90.0, "Army's Paeon"),
            (135.0, "The Wanderer's Minuet"),
        ]:
            self.use(state, song, t)
        self.use(state, "Radiant Finale", 136.0)
        self.assertAlmostEqual(state.active_damage_buffs(137.0)["damage_mult"], 1.06)
        self.assertEqual(self.use(state, "Radiant Encore", 137.0)[1], 1100)

    def test_barrage_resonant_and_barrage_potencies(self):
        state = BrdJobState()

        self.use(state, "Barrage", 0.0)
        payload, potency, _dots, followups = self.use(state, "Refulgent Arrow", 1.0)
        self.assertEqual(potency, 840)
        self.assertNotIn("brd_barrage_refulgent", payload)
        self.assertEqual(followups, [])
        self.assertEqual(state.barrage_until, -1.0)
        self.assertGreater(state.resonant_arrow_until, 1.0)

        self.use(state, "Resonant Arrow", 2.0)
        self.assertEqual(state.resonant_arrow_until, -1.0)

        self.use(state, "Barrage", 3.0)
        _payload, potency, _dots, followups = self.use(state, "Shadowbite", 4.0)
        self.assertEqual(potency, 300)
        self.assertEqual(followups, [])

    def test_repertoire_pitch_apex_and_blast(self):
        state = BrdJobState()

        self.use(state, "The Wanderer's Minuet", 0.0)
        self.use(state, "Empyreal Arrow", 1.0)
        self.assertEqual(state.pitch_stacks, 1)
        self.assertEqual(self.use(state, "Pitch Perfect", 2.0)[1], 360)
        self.assertEqual(state.pitch_stacks, 0)

        state.soul_voice = 80
        self.assertEqual(self.use(state, "Apex Arrow", 3.0)[1], 560)
        self.assertEqual(state.soul_voice, 0)
        self.assertGreater(state.blast_arrow_until, 3.0)
        self.use(state, "Blast Arrow", 4.0)
        self.assertEqual(state.blast_arrow_until, -1.0)

    def test_triggered_actions_in_axis_are_treated_as_ready(self):
        state = BrdJobState()

        self.assertEqual(self.use(state, "Pitch Perfect", 0.0)[1], 360)
        self.assertEqual(self.use(state, "Apex Arrow", 1.0)[1], 700)
        self.assertEqual(self.use(state, "Blast Arrow", 2.0)[1], 700)
        self.assertEqual(self.use(state, "Radiant Encore", 3.0)[1], 1100)
        self.assertEqual(self.use(state, "Resonant Arrow", 4.0)[1], 640)
        self.assertEqual(state.get_resource_warnings(), [])

    def test_iron_jaws_refreshes_any_active_dot(self):
        state = BrdJobState()

        self.use(state, "Caustic Bite", 0.0)
        _payload, _potency, dots, _followups = self.use(state, "Iron Jaws", 10.0)
        self.assertEqual([dot["dot_key"] for dot in dots], ["brd_caustic"])
        self.assertEqual(state.get_resource_warnings(), [])

        self.use(state, "Stormbite", 20.0)
        _payload, _potency, dots, _followups = self.use(state, "Iron Jaws", 25.0)
        self.assertEqual([dot["dot_key"] for dot in dots], ["brd_caustic", "brd_storm"])

        empty_state = BrdJobState()
        _payload, _potency, dots, _followups = self.use(empty_state, "Iron Jaws", 0.0)
        self.assertEqual(dots, [])
        self.assertEqual(
            [warning["code"] for warning in empty_state.get_resource_warnings()],
            ["brd_iron_jaws_missing_dot"],
        )

    def test_brd_long_axis_has_only_tracked_axis_warnings(self):
        path = REPO_ROOT / "examples" / "skill_lines" / "brd_xivintheshell_long" / "brd_xivintheshell_long.csv"
        events, _meta = parse_axis_csv(
            path,
            normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, "BRD"),
        )
        result = DpsSimulator(dict(BASE_STATS), events, iterations=1).run_one_simulation(is_first_run=True)
        self.assertGreater(result[0], 0)
        codes = {warning["code"] for warning in result[-1]}
        self.assertLessEqual(codes, {"brd_iron_jaws_missing_dot"})


if __name__ == "__main__":
    unittest.main()
