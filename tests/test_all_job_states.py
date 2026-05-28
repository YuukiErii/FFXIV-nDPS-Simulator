import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from jobs import MODELED_JOB_STATE_SKILLS, create_job_state  # noqa: E402
from jobs.drg import DrgJobState  # noqa: E402
from jobs.mch import MchJobState  # noqa: E402
from scan_skill_coverage import is_known_non_axis_csv  # noqa: E402
from sim import (  # noqa: E402
    DpsSimulator,
    SkillResolver,
    build_skill_coverage,
    normalize_skill_name_for_job,
)
from xiv_axis_csv import parse_axis_csv  # noqa: E402


BASE_STATS = {
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "delay": 2.64,
}


JOB_SMOKE_TIMELINES = {
    "SAM": [(0.0, "Hakaze", 1), (2.5, "Jinpu", 1), (5.0, "Gekko", 1)],
    "MNK": [(0.0, "Riddle of Fire", 1), (1.0, "Dragon Kick", 1), (3.5, "Twin Snakes", 1), (6.0, "Demolish", 1)],
    "DRG": [(0.0, "Lance Charge", 1), (1.0, "True Thrust", 1), (3.5, "Spiral Blow", 1), (6.0, "Chaotic Spring", 1)],
    "NIN": [(0.0, "Dokumori", 1), (1.0, "Spinning Edge", 1), (3.5, "Gust Slash", 1), (6.0, "Aeolian Edge", 1)],
    "RPR": [(0.0, "Shadow of Death", 1), (2.5, "Slice", 1), (5.0, "Waxing Slice", 1), (7.5, "Infernal Slice", 1)],
    "VPR": [(0.0, "Hunter's Sting", 1), (2.5, "Swiftskin's Sting", 1), (5.0, "Reawaken", 1), (7.5, "First Generation", 1)],
    "BRD": [(0.0, "Raging Strikes", 1), (1.0, "Caustic Bite", 1), (3.5, "Stormbite", 1), (6.0, "Burst Shot", 1)],
    "MCH": [(0.0, "Reassemble", 1), (1.0, "Drill", 1), (3.5, "Wildfire", 1), (4.5, "Heat Blast", 1), (6.0, "Heat Blast", 1)],
    "DNC": [(0.0, "Standard Finish", 1), (2.5, "Devilment", 1), (3.5, "Saber Dance", 1), (6.0, "Starfall Dance", 1)],
    "BLM": [(0.0, "Fire 3", 1), (2.5, "Fire 4", 1), (5.0, "Despair", 1)],
    "SMN": [(0.0, "Searing Light", 1), (1.0, "Summon Bahamut", 1), (4.0, "Deathflare", 1), (6.0, "Akh Morn", 1)],
    "RDM": [(0.0, "Embolden", 1), (1.0, "Manafication", 1), (2.0, "Enchanted Riposte", 1), (4.5, "Enchanted Zwerchhau", 1), (7.0, "Enchanted Redoublement", 1)],
    "PCT": [(0.0, "Starry Muse", 1), (1.0, "Fire in Red", 1), (3.5, "Hammer Stamp", 1), (6.0, "Star Prism", 1)],
}

XIVINTHESHELL_SMOKE_CSVS = {
    "MNK": REPO_ROOT / "examples/skill_lines" / "mnk_xivintheshell_smoke" / "mnk_xivintheshell_smoke.csv",
    "DRG": REPO_ROOT / "examples/skill_lines" / "drg_xivintheshell_smoke" / "drg_xivintheshell_smoke.csv",
    "VPR": REPO_ROOT / "examples/skill_lines" / "vpr_xivintheshell_smoke" / "vpr_xivintheshell_smoke.csv",
    "BRD": REPO_ROOT / "examples/skill_lines" / "brd_xivintheshell_smoke" / "brd_xivintheshell_smoke.csv",
    "MCH": REPO_ROOT / "examples/skill_lines" / "mch_xivintheshell_smoke" / "mch_xivintheshell_smoke.csv",
    "DNC": REPO_ROOT / "examples/skill_lines" / "dnc_xivintheshell_smoke" / "dnc_xivintheshell_smoke.csv",
    "SMN": REPO_ROOT / "examples/skill_lines" / "smn_xivintheshell_smoke" / "smn_xivintheshell_smoke.csv",
    "RDM": REPO_ROOT / "examples/skill_lines" / "rdm_xivintheshell_smoke" / "rdm_xivintheshell_smoke.csv",
}

XIVINTHESHELL_LONG_CSVS = {
    "MNK": REPO_ROOT / "examples/skill_lines" / "mnk_xivintheshell_long" / "mnk_xivintheshell_long.csv",
    "DRG": REPO_ROOT / "examples/skill_lines" / "drg_xivintheshell_long" / "drg_xivintheshell_long.csv",
    "VPR": REPO_ROOT / "examples/skill_lines" / "vpr_xivintheshell_long" / "vpr_xivintheshell_long.csv",
    "BRD": REPO_ROOT / "examples/skill_lines" / "brd_xivintheshell_long" / "brd_xivintheshell_long.csv",
    "MCH": REPO_ROOT / "examples/skill_lines" / "mch_xivintheshell_long" / "mch_xivintheshell_long.csv",
    "DNC": REPO_ROOT / "examples/skill_lines" / "dnc_xivintheshell_long" / "dnc_xivintheshell_long.csv",
    "SMN": REPO_ROOT / "examples/skill_lines" / "smn_xivintheshell_long" / "smn_xivintheshell_long.csv",
    "RDM": REPO_ROOT / "examples/skill_lines" / "rdm_xivintheshell_long" / "rdm_xivintheshell_long.csv",
}


class AllJobStateTests(unittest.TestCase):
    def test_all_dps_jobs_have_specific_state_classes(self):
        for job in JOB_SMOKE_TIMELINES:
            with self.subTest(job=job):
                state = create_job_state(job)
                self.assertNotEqual(type(state).__name__, "JobState")

    def test_key_smoke_timelines_are_known_and_runnable(self):
        for job, timeline in JOB_SMOKE_TIMELINES.items():
            resolver = SkillResolver(job)
            if resolver.provider is None:
                self.skipTest("AMAS skill provider is unavailable")

            with self.subTest(job=job):
                for _, name, _ in timeline:
                    cls = resolver.classify_skill(name)
                    self.assertTrue(cls["known"], name)
                    self.assertFalse(cls["needs_state"], name)
                    self.assertFalse(cls["followup_unmodeled"], name)

                stats = dict(BASE_STATS)
                stats["job"] = job
                sim = DpsSimulator(stats, timeline, iterations=1)
                total, duration, *_ = sim.run_one_simulation(is_first_run=False)
                self.assertGreater(duration, 0)
                self.assertGreater(total, 0)

    def test_xivintheshell_smoke_csvs_are_known_and_runnable(self):
        for job, path in XIVINTHESHELL_SMOKE_CSVS.items():
            resolver = SkillResolver(job)
            if resolver.provider is None:
                self.skipTest("AMAS skill provider is unavailable")

            with self.subTest(job=job):
                events, meta = parse_axis_csv(
                    path,
                    normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job),
                )
                report = build_skill_coverage(events, resolver, csv_meta=meta)
                stats = report["stats"]
                self.assertEqual(stats.get("unrecognized_events", 0), 0)
                self.assertEqual(stats.get("needs_state_events", 0), 0)
                self.assertEqual(stats.get("followup_unmodeled_events", 0), 0)

                sim_stats = dict(BASE_STATS)
                sim_stats["job"] = job
                sim = DpsSimulator(sim_stats, events, iterations=1)
                total, duration, *_ = sim.run_one_simulation(is_first_run=False)
                self.assertGreater(duration, 0)
                self.assertGreater(total, 0)

    def test_xivintheshell_long_csvs_are_known_and_runnable(self):
        for job, path in XIVINTHESHELL_LONG_CSVS.items():
            resolver = SkillResolver(job)
            if resolver.provider is None:
                self.skipTest("AMAS skill provider is unavailable")

            with self.subTest(job=job):
                events, meta = parse_axis_csv(
                    path,
                    normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job),
                )
                self.assertGreaterEqual(len(events), 45)
                self.assertGreaterEqual(max(event["time"] for event in events), 135)
                report = build_skill_coverage(events, resolver, csv_meta=meta)
                stats = report["stats"]
                self.assertEqual(stats.get("unrecognized_events", 0), 0)
                self.assertEqual(stats.get("needs_state_events", 0), 0)
                self.assertEqual(stats.get("followup_unmodeled_events", 0), 0)

                sim_stats = dict(BASE_STATS)
                sim_stats["job"] = job
                sim = DpsSimulator(sim_stats, events, iterations=1)
                total, duration, *_ = sim.run_one_simulation(is_first_run=False)
                self.assertGreater(duration, 135)
                self.assertGreater(total, 0)

    def test_coverage_directory_scan_skips_damage_exports(self):
        damage_path = REPO_ROOT / "examples/skill_lines" / "mnk_xivintheshell_long" / "mnk_xivintheshell_damage.csv"
        axis_path = REPO_ROOT / "examples/skill_lines" / "mnk_xivintheshell_long" / "mnk_xivintheshell_long.csv"
        self.assertTrue(is_known_non_axis_csv(damage_path))
        self.assertFalse(is_known_non_axis_csv(axis_path))

    def test_modeled_skill_lists_resolve_to_known_skills(self):
        for job, names in MODELED_JOB_STATE_SKILLS.items():
            resolver = SkillResolver(job)
            if resolver.provider is None:
                self.skipTest("AMAS skill provider is unavailable")
            for name in names:
                with self.subTest(job=job, name=name):
                    self.assertTrue(resolver.classify_skill(name)["known"])

    def test_mch_wildfire_counts_weaponskill_hits(self):
        state = MchJobState()
        state.on_press("Wildfire", {"amas_name": "Wildfire", "potency": 0}, 0.0, 0.0)
        state.on_press_complete("Wildfire", 0.0)
        for t in [1, 2, 3, 4, 5, 6, 7]:
            state.on_damage_resolved("Heat Blast", {"amas_name": "Heat Blast", "potency": 240}, float(t), False, {})

        potency, _ = state.resolve_potency("Wildfire", {"amas_name": "Wildfire", "potency": 0}, 10.0, {})
        self.assertEqual(potency, 1440)

    def test_mch_wildfire_and_queen_are_attributed_separately(self):
        timeline = [
            (0.0, "Wildfire", 1),
            (1.0, "Heat Blast", 1),
            (2.0, "Heat Blast", 1),
            (3.0, "Heat Blast", 1),
            (4.0, "Heat Blast", 1),
            (5.0, "Heat Blast", 1),
            (6.0, "Detonator", 1),
            (20.0, "Automaton Queen", 1),
        ]
        stats = dict(BASE_STATS)
        stats["job"] = "MCH"
        sim = DpsSimulator(stats, timeline, iterations=1)
        total, _duration, dmg, counts, *_ = sim.run_one_simulation(is_first_run=True)

        self.assertGreater(total, 0)
        self.assertGreater(dmg.get("Wildfire", 0), 0)
        self.assertEqual(dmg.get("Detonator", 0), 0)
        self.assertEqual(counts.get("Armpunch", 0), 5)
        self.assertEqual(counts.get("Pilebunker", 0), 1)
        self.assertEqual(counts.get("Crowned Collider", 0), 1)

    def test_smn_pet_followups_are_attributed_separately(self):
        timeline = [
            (0.0, "Summon Bahamut", 1),
            (20.0, "Summon Ifrit II", 1),
            (40.0, "Summon Phoenix", 1),
            (43.0, "Enkindle Phoenix", 1),
        ]
        stats = dict(BASE_STATS)
        stats["job"] = "SMN"
        sim = DpsSimulator(stats, timeline, iterations=1)
        total, _duration, _dmg, counts, *_ = sim.run_one_simulation(is_first_run=True)

        self.assertGreater(total, 0)
        self.assertEqual(counts.get("Summon Bahamut", 0), 1)
        self.assertEqual(counts.get("Wyrmwave", 0), 4)
        self.assertEqual(counts.get("Inferno", 0), 1)
        self.assertEqual(counts.get("Scarlet Flame", 0), 4)
        self.assertEqual(counts.get("Revelation", 0), 1)

    def test_dot_ticks_are_attributed_to_source_skill(self):
        timeline = [
            (0.0, "Slipstream", 1),
            (15.0, "Ruin III", 1),
        ]
        stats = dict(BASE_STATS)
        stats["job"] = "SMN"
        sim = DpsSimulator(stats, timeline, iterations=1)
        total, _duration, _dmg, counts, *_ = sim.run_one_simulation(is_first_run=True)

        self.assertGreater(total, 0)
        self.assertNotIn("Dot Tick", counts)
        self.assertGreater(counts.get("Slipstream", 0), 1)

    def test_rdm_allows_caster_auto_attacks(self):
        stats = dict(BASE_STATS)
        stats["job"] = "RDM"
        timeline = [
            (0.0, "Enchanted Riposte", 1),
            (10.0, "Jolt III", 1),
        ]
        sim = DpsSimulator(stats, timeline, iterations=1)
        total, _duration, _dmg, counts, *_ = sim.run_one_simulation(is_first_run=True)

        self.assertGreater(total, 0)
        self.assertGreater(counts.get("Auto Attack", 0), 0)

    def test_resource_warnings_are_non_blocking(self):
        def row(time, name, row_no, targets=1):
            return {"time": time, "name": name, "targets": targets, "row_no": row_no}

        cases = {
            "SAM": [row(0.0, "Hissatsu: Shinten", 101)],
            "MNK": [row(0.0, "The Forbidden Chakra", 102)],
            "DRG": [row(0.0, "Nastrond", 103)],
            "NIN": [row(0.0, "Raiton", 104)],
            "RPR": [row(0.0, "Void Reaping", 105)],
            "VPR": [row(0.0, "First Generation", 106)],
            "BRD": [row(0.0, "Iron Jaws", 107), row(2.5, "Burst Shot", 108)],
            "MCH": [row(0.0, "Hypercharge", 109), row(0.7, "Heat Blast", 110), row(3.0, "Automaton Queen", 111)],
            "DNC": [row(0.0, "Standard Finish", 112)],
            "BLM": [row(0.0, "Fire IV", 113)],
            "SMN": [row(0.0, "Ruby Rite", 114), row(2.5, "Necrotize", 115)],
            "RDM": [row(0.0, "Enchanted Riposte", 116), row(2.5, "Enchanted Zwerchhau", 117), row(5.0, "Enchanted Redoublement", 118)],
            "PCT": [row(0.0, "Pom Muse", 119)],
        }
        for job, timeline in cases.items():
            with self.subTest(job=job):
                stats = dict(BASE_STATS)
                stats["job"] = job
                if job == "RDM":
                    stats["main_stat"] = 5925
                    stats["wd"] = 152
                    stats["sks"] = 547
                sim = DpsSimulator(stats, timeline, iterations=1)
                result = sim.run_one_simulation(is_first_run=True)
                total = result[0]
                warnings = result[-1]

                self.assertGreater(total, 0)
                self.assertGreater(len(warnings), 0)
                self.assertIn("message", warnings[0])
                self.assertIn("row_no", warnings[0])

    def test_single_hit_forced_crit_states(self):
        mch = MchJobState()
        mch.on_damage_resolved("Reassemble", {"amas_name": "Reassemble", "potency": 0}, 0.0, False, {})
        self.assertEqual(
            mch.on_press("Drill", {"amas_name": "Drill", "potency": 600}, 1.0, 1.0),
            {"guaranteed_crit": True, "guaranteed_dh": True},
        )

        drg = DrgJobState()
        drg.on_damage_resolved("Life Surge", {"amas_name": "Life Surge", "potency": 0}, 0.0, False, {})
        self.assertEqual(
            drg.on_press("Heavens' Thrust", {"amas_name": "Heavens' Thrust", "potency": 440}, 1.0, 1.0),
            {"guaranteed_crit": True},
        )


if __name__ == "__main__":
    unittest.main()
