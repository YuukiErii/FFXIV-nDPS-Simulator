import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from jobs.dnc import DncJobState  # noqa: E402
from sim import DpsSimulator, SkillResolver, normalize_skill_name_for_job  # noqa: E402
from xiv_axis_csv import parse_axis_csv  # noqa: E402


BASE_STATS = {
    "job": "DNC",
    "main_stat": 5925,
    "crt": 3427,
    "det": 2300,
    "dh": 1890,
    "sks": 420,
    "wd": 152,
}


class DncJobStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = SkillResolver("DNC", "7.5")
        if cls.resolver.provider is None:
            raise unittest.SkipTest("AMAS skill provider is unavailable")

    def use(self, state, name, t=0.0):
        skill = self.resolver.get(name)
        state.set_event_context({})
        press_state = state.on_press(name, skill, t, t)
        payload = {"is_gcd": skill.get("is_gcd"), "targets": 1, **press_state}
        state.on_press_confirmed(name, skill, t, payload)
        potency, is_combo = state.resolve_potency(name, skill, t, payload)
        state.on_damage_resolved(name, skill, t + skill.get("delay", 0.0), is_combo, payload)
        return payload, potency

    def test_technical_finish_defaults_to_four_steps(self):
        state = DncJobState()
        _payload, potency = self.use(state, "Technical Finish", 0.0)
        self.assertEqual(potency, 1300)
        self.assertEqual(state.technical_mult, 1.05)
        self.assertNotIn("dnc_technical_finish_steps_low", {w["code"] for w in state.get_resource_warnings()})

    def test_explicit_finish_variants_are_state_handled(self):
        state = DncJobState()
        for name, potency, mult in [
            ("Single Technical Finish", 540, 1.01),
            ("Double Technical Finish", 720, 1.02),
            ("Triple Technical Finish", 900, 1.03),
            ("Quadruple Technical Finish", 1300, 1.05),
        ]:
            with self.subTest(name=name):
                self.assertTrue(state.handles_skill_buff(name, self.resolver.get(name)))
                state = DncJobState()
                _payload, actual = self.use(state, name, 0.0)
                self.assertEqual(actual, potency)
                self.assertEqual(state.technical_mult, mult)

    def test_triggered_actions_in_axis_are_treated_as_ready(self):
        state = DncJobState()
        for name in ("Fan Dance III", "Fan Dance IV", "Saber Dance", "Dance of the Dawn", "Starfall Dance"):
            self.use(state, name, 1.0)
        self.assertEqual(state.get_resource_warnings(), [])

    def test_tillana_and_esprit_spenders(self):
        state = DncJobState()
        self.use(state, "Tillana", 0.0)
        self.assertEqual(state.esprit, 50)
        self.use(state, "Dance of the Dawn", 2.5)
        self.assertEqual(state.esprit, 0)

    def test_enhanced_esprit_gcds_gain_ten(self):
        state = DncJobState()
        self.use(state, "Standard Finish", 0.0)
        self.use(state, "Cascade", 2.5)
        self.assertEqual(state.esprit, 5)
        self.use(state, "Reverse Cascade", 5.0)
        self.assertEqual(state.esprit, 15)

    def test_dnc_long_axis_has_tracked_resources(self):
        path = REPO_ROOT / "examples" / "skill_lines" / "dnc_xivintheshell_long" / "dnc_xivintheshell_long.csv"
        events, _meta = parse_axis_csv(
            path,
            normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, "DNC"),
        )
        result = DpsSimulator(dict(BASE_STATS), events, iterations=1).run_one_simulation(is_first_run=True)
        self.assertGreater(result[0], 0)
        self.assertEqual(result[-1], [])


if __name__ == "__main__":
    unittest.main()
