import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from xiv_damage_formula import DamageModifiers, FormulaStats, XivDamageFormula  # noqa: E402


class DamageFormulaTests(unittest.TestCase):
    def setUp(self):
        stats = FormulaStats.from_job(
            job="SAM",
            main_stat=6498,
            crit=3605,
            det=2426,
            dh=1793,
            speed=689,
            wd=158,
            weapon_delay=2.64,
            party_bonus=1.05,
        )
        self.formula = XivDamageFormula(stats)

    def test_level_100_stat_functions_match_smoke_values(self):
        self.assertEqual(self.formula.f_wd(), 207)
        self.assertEqual(self.formula.f_auto(), 182)
        self.assertEqual(self.formula.f_det(), 1100)
        self.assertEqual(self.formula.f_spd(), 1012)
        self.assertAlmostEqual(self.formula.crit_rate(), 0.279)
        self.assertAlmostEqual(self.formula.crit_multiplier(), 1.629)
        self.assertAlmostEqual(self.formula.direct_hit_rate(), 0.271)

    def test_base_damage_channels_match_smoke_values(self):
        self.assertEqual(self.formula.base_direct_damage(420), 33823)
        self.assertEqual(self.formula.base_physical_dot_damage(50), 4073)
        self.assertEqual(self.formula.base_auto_damage(90), 6448)

    def test_expected_damage_is_deterministic(self):
        base = self.formula.base_direct_damage(420)
        breakdown = self.formula.damage_breakdown(base)
        self.assertAlmostEqual(breakdown.expected, 42451.915271, places=6)

    def test_forced_crit_direct_hit_uses_bonus_rates(self):
        base = self.formula.base_direct_damage(
            420,
            DamageModifiers(forced_crit=True, forced_dh=True, crit_rate_add=0.1, dh_rate_add=0.1),
        )
        self.assertGreater(base, self.formula.base_direct_damage(420))


if __name__ == "__main__":
    unittest.main()
