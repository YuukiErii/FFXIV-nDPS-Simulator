import math
import random
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from xiv_damage_formula import DamageModifiers, FormulaStats, XivDamageFormula  # noqa: E402


def assert_close(name, actual, expected, tol=1e-9):
    if not math.isclose(actual, expected, rel_tol=0, abs_tol=tol):
        raise AssertionError(f"{name}: expected {expected}, got {actual}")


def assert_equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected}, got {actual}")


def main():
    formula = XivDamageFormula(
        FormulaStats.from_job(
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
    )

    assert_close("crit_rate", formula.crit_rate(), 0.279)
    assert_close("crit_bonus", formula.crit_bonus(), 0.629)
    assert_close("crit_multiplier", formula.crit_multiplier(), 1.629)
    assert_close("direct_hit_rate", formula.direct_hit_rate(), 0.271)
    assert_equal("f_det", formula.f_det(), 1100)
    assert_equal("f_spd", formula.f_spd(), 1012)
    assert_equal("f_wd", formula.f_wd(), 207)
    assert_equal("f_auto", formula.f_auto(), 182)
    assert_close("gcd_base", formula.gcd_seconds()[0], 2.470)
    assert_close("gcd_job", formula.gcd_seconds()[1], 2.148)

    direct = formula.base_direct_damage(420)
    dot = formula.base_physical_dot_damage(50)
    auto = formula.base_auto_damage(90)
    assert_equal("direct_base_420", direct, 33823)
    assert_equal("physical_dot_base_50", dot, 4073)
    assert_equal("auto_base_90", auto, 6448)

    direct_breakdown = formula.damage_breakdown(direct)
    assert_equal("direct_normal", direct_breakdown.normal, 33823)
    assert_equal("direct_crit", direct_breakdown.crit, 55097)
    assert_equal("direct_dh", direct_breakdown.direct_hit, 42278)
    assert_equal("direct_cdh", direct_breakdown.crit_direct_hit, 68871)
    assert_close("direct_expected", direct_breakdown.expected, 42451.915271000005)

    mod = DamageModifiers(main_stat_add=432, forced_crit=True, crit_rate_add=0.10)
    forced_base = formula.base_direct_damage(680, mod)
    forced_breakdown = formula.damage_breakdown(forced_base, mod)
    assert_equal("forced_crit_base", forced_base, 62042)
    assert_close("forced_crit_rate", forced_breakdown.crit_rate, 1.0)
    assert_equal("forced_crit_damage", forced_breakdown.crit, 101066)

    rng = random.Random(1234)
    rolled = formula.roll_damage(direct, rng=rng)
    assert_equal("seeded_roll_damage", rolled[0], 32157)
    assert_equal("seeded_roll_crit", rolled[1], False)
    assert_equal("seeded_roll_dh", rolled[2], False)

    print("damage formula smoke ok")
    print(f"direct_base_420={direct} dot_base_50={dot} auto_base_90={auto}")
    print(f"direct_expected={direct_breakdown.expected:.6f}")


if __name__ == "__main__":
    raise SystemExit(main())
