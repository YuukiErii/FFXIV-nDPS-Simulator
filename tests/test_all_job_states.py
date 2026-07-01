import pathlib
import random
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from jobs import MODELED_JOB_STATE_SKILLS, create_job_state  # noqa: E402
from jobs.base import JobState  # noqa: E402
from jobs.drg import DrgJobState  # noqa: E402
from jobs.mch import MchJobState  # noqa: E402
from jobs.sam import SamJobState  # noqa: E402
from scan_skill_coverage import is_known_non_axis_csv  # noqa: E402
from run_ndps_simulation import _target_record, _target_record_downtime, run as run_backend_simulation  # noqa: E402
from sim import (  # noqa: E402
    DpsSimulator,
    SkillResolver,
    build_skill_coverage,
    normalize_skill_name_for_job,
)
from xiv_axis_csv import parse_axis_csv  # noqa: E402
from xiv_sim_core import parse_downtime_windows, parse_marker_track_downtime_windows, total_window_overlap  # noqa: E402


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

UNTARGETABLE_TRACK = REPO_ROOT / "examples/skill_lines" / "sam_dmu" / "track_untargetable.txt"
SAM_DMU_CSV = REPO_ROOT / "examples/skill_lines" / "sam_dmu" / "2.17.csv"
SAM_DMU_TARGET = REPO_ROOT / "examples/skill_lines" / "sam_dmu" / "2.17.txt"


class AllJobStateTests(unittest.TestCase):
    def test_global_downtime_accepts_multiple_windows(self):
        windows = parse_downtime_windows("(10, 20)\n30-35; 40，45")
        self.assertEqual(windows, [(10.0, 20.0), (30.0, 35.0), (40.0, 45.0)])
        self.assertEqual(total_window_overlap(windows, 42.0), 17.0)

    def test_untargetable_marker_track_becomes_global_downtime(self):
        text = UNTARGETABLE_TRACK.read_text(encoding="utf-8-sig")
        windows = parse_marker_track_downtime_windows(text)

        self.assertGreaterEqual(len(windows), 1)
        self.assertTrue(all(start < end for start, end in windows))
        self.assertAlmostEqual(windows[0][0], 197.597)
        self.assertAlmostEqual(windows[0][1], 207.933)
        self.assertEqual(parse_downtime_windows(text), windows)
        self.assertEqual(_target_record_downtime(_target_record(UNTARGETABLE_TRACK)), windows)

    def test_backend_accepts_target_and_untargetable_track_together(self):
        result = run_backend_simulation(
            {
                "csv_path": str(SAM_DMU_CSV),
                "target_path": str(SAM_DMU_TARGET),
                "downtime_track_path": str(UNTARGETABLE_TRACK),
                "job": "SAM",
                "iterations": 1,
                "threshold": 0,
                "stats": dict(BASE_STATS, party_bonus=1.05, version="7.5"),
            }
        )

        self.assertEqual(result["metadata"]["global_downtime_source"], "downtime_track_path")
        self.assertTrue(result["metadata"]["target_path"].endswith("2.17.txt"))
        self.assertTrue(result["metadata"]["downtime_track_path"].endswith("track_untargetable.txt"))
        self.assertGreater(result["summary"]["expected_dps"], 0)
        self.assertIn("skill_data_source", result["metadata"])
        self.assertIn("crit_rate", result["panel"])
        self.assertGreater(len(result["skills"]), 0)
        self.assertGreater(len(result["best_run"]), 0)
        self.assertGreater(len(result["intervals"]), 0)
        self.assertGreater(len(result["combat_log"]), 0)
        self.assertIn("invalid_skill_events", result)
        self.assertEqual(result["preview"]["total"], result["coverage"]["stats"]["total_events"])
        self.assertIn("row_no", result["preview"]["rows"][0])

    def test_duration_uses_last_damage_application_not_last_button_press(self):
        stats = dict(BASE_STATS, job="SAM", version="7.5", party_bonus=1.05)
        damage_event = {"time": 0.0, "name": "晓风", "targets": 1}
        sim = DpsSimulator(
            stats,
            [damage_event, {"time": 10.0, "name": "明镜止水", "targets": 1}],
            iterations=1,
        )
        skill = sim.get_skill(damage_event["name"])
        expected_last_hit = sim.effective_cast_time(skill, damage_event) + skill.get("delay", 0.5)

        with patch.object(random, "random", return_value=1.0), patch.object(
                random, "uniform", side_effect=lambda low, high: (low + high) / 2):
            _total, last_hit, _dmg, counts, *_ = sim.run_one_simulation(is_first_run=True)

        self.assertAlmostEqual(last_hit, expected_last_hit, places=6)
        self.assertEqual(counts["晓风"], 1)

    def test_target_damage_pressed_during_downtime_warns_and_does_not_resolve(self):
        stats = dict(BASE_STATS, job="SAM", version="7.5", party_bonus=1.05)
        skill_name = "\u6653\u98ce"
        sim = DpsSimulator(
            stats,
            [{"time": 0.05, "name": skill_name, "targets": 1}],
            iterations=1,
            global_downtime_list=[(0.0, 0.1)],
        )

        with patch.object(random, "random", return_value=1.0), patch.object(
                random, "uniform", side_effect=lambda low, high: (low + high) / 2):
            result = sim.run_one_simulation(is_first_run=True)

        total, _last_hit, damage, counts = result[:4]
        log = result[8]
        warnings = result[-1]

        self.assertEqual(total, 0)
        self.assertEqual(counts[skill_name], 0)
        self.assertEqual(damage[skill_name], 0)
        self.assertEqual(log[0]["buffs"], "Interrupted")
        self.assertEqual(warnings[0]["code"], "target_untargetable_at_press")

    def test_invalid_skill_events_include_zero_damage_and_downtime_press(self):
        stats = dict(BASE_STATS, job="SAM", version="7.5", party_bonus=1.05)
        skill_name = "\u6653\u98ce"
        sim = DpsSimulator(
            stats,
            [
                {"time": 0.0, "name": "Sprint", "targets": 1, "row_no": 1},
                {"time": 0.05, "name": skill_name, "targets": 1, "row_no": 2},
            ],
            iterations=1,
            global_downtime_list=[(0.0, 0.1)],
        )

        with patch.object(random, "random", return_value=1.0), patch.object(
                random, "uniform", side_effect=lambda low, high: (low + high) / 2):
            _dps, _duration, _last_hit, stats_pkg, _log = sim.run_batch()

        invalid = stats_pkg["invalid_skill_events"]
        self.assertIn("zero_damage", {item["code"] for item in invalid})
        self.assertIn("target_untargetable_at_press", {item["code"] for item in invalid})
        self.assertEqual([item["row_no"] for item in invalid], [1, 2])

    def test_targetless_aoe_pressed_during_downtime_uses_damage_application_time(self):
        stats = dict(BASE_STATS, job="VPR", version="7.5", party_bonus=1.05)
        skill_name = "Steel Maw"
        sim = DpsSimulator(
            stats,
            [{"time": 0.05, "name": skill_name, "targets": 1}],
            iterations=1,
            global_downtime_list=[(0.0, 0.1)],
        )
        skill = sim.get_skill(skill_name)

        with patch.object(random, "random", return_value=1.0), patch.object(
                random, "uniform", side_effect=lambda low, high: (low + high) / 2):
            result = sim.run_one_simulation(is_first_run=True)

        total, last_hit, damage, counts = result[:4]
        log = result[8]
        warnings = result[-1]

        self.assertAlmostEqual(last_hit, 0.05 + skill["delay"], places=6)
        self.assertGreater(total, 0)
        self.assertEqual(counts[skill_name], 1)
        self.assertGreater(damage[skill_name], 0)
        self.assertAlmostEqual(log[0]["time"], 0.05 + skill["delay"], places=6)
        self.assertNotIn("\u514d\u75ab", str(log[0]["dmg"]))
        self.assertNotIn("target_untargetable_at_press", {warning["code"] for warning in warnings})

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

    def test_sam_provider_keeps_backup_authoritative_overlay(self):
        resolver = SkillResolver("SAM")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        gekko = resolver.get("Gekko")
        midare = resolver.get("Midare Setsugekka")
        ogi = resolver.get("Ogi Namikiri")

        self.assertEqual(gekko["base_potency"], 210)
        self.assertEqual(gekko["meikyo_grants"], "fugetsu")
        self.assertEqual(midare["potency"], 680)
        self.assertEqual(ogi["decay"], 0.4)

    def test_xivintheshell_application_delay_overrides_are_applied(self):
        cases = {
            "SAM": {"Tendo Goken": 0.36, "Tendo Kaeshi Goken": 0.36},
            "MNK": {"Six-sided Star": 0.62, "The Forbidden Chakra": 1.48},
            "NIN": {"Huton": 0.98},
            "VPR": {"Hunter's Sting": 0.89, "Swiftskin's Den": 0.999, "Vicepit": 0.827},
            "MCH": {"Flamethrower": 0.89, "Full Metal Field": 1.02},
            "DNC": {"Dance of the Dawn": 0.44},
            "BLM": {"Fire IV": 1.159, "Blizzard IV": 1.156, "Despair": 0.556},
            "SMN": {"Topaz Rite": 0.62},
            "RDM": {"Riposte": 0.62},
        }

        for job, skills in cases.items():
            resolver = SkillResolver(job, "7.5")
            if resolver.provider is None:
                self.skipTest("AMAS skill provider is unavailable")
            for name, expected_delay in skills.items():
                with self.subTest(job=job, skill=name):
                    skill = resolver.get(name)
                    self.assertIsNotNone(skill)
                    self.assertAlmostEqual(skill["delay"], expected_delay)

    def test_sam_meikyo_gekko_grants_fugetsu(self):
        resolver = SkillResolver("SAM")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = SamJobState()
        gekko = resolver.get("Gekko")
        state.on_press_complete("明镜止水", 0.0)
        payload = {"meikyo": state.consume_combo_override("月光", gekko, 1.0)}
        potency, is_combo = state.resolve_potency("月光", gekko, 1.0, payload)
        state.on_damage_resolved("月光", gekko, 1.0, is_combo, payload)

        self.assertEqual(potency, 420)
        self.assertTrue(is_combo)
        self.assertTrue(state.active_damage_buffs(1.1)["sam_fugetsu"])

    def test_sam_ogcd_does_not_break_combo_chain(self):
        resolver = SkillResolver("SAM")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        state = SamJobState()
        for t, name in [(0.0, "Gyofu"), (2.5, "Jinpu"), (3.0, "Hissatsu: Shinten")]:
            skill = resolver.get(name)
            potency, is_combo = state.resolve_potency(name, skill, t, {})
            self.assertGreater(potency, 0)
            state.on_damage_resolved(name, skill, t, is_combo, {})

        gekko = resolver.get("Gekko")
        potency, is_combo = state.resolve_potency("Gekko", gekko, 5.0, {})
        self.assertTrue(is_combo)
        self.assertEqual(potency, 420)

    def test_sam_confirm_resources_are_ready_before_application_delay(self):
        state = SamJobState()
        state.sen = {"setsu", "getsu", "ka"}
        state.meditation_stacks = 2
        state.on_press("天道雪月花", {"amas_name": "Tendo Setsugekka", "potency": 1100}, 0.0, 0.8)
        state.on_press_complete("天道雪月花", 0.0)
        state.on_press("天道回返雪月花", {"amas_name": "Tendo Kaeshi Setsugekka", "potency": 1100}, 2.14, 2.14)
        state.on_press("照破", {"amas_name": "Shoha", "potency": 640}, 2.15, 2.15)

        codes = [warning["code"] for warning in state.get_resource_warnings()]
        self.assertNotIn("sam_kaeshi_not_ready", codes)
        self.assertNotIn("sam_meditation_low", codes)

    def test_sam_meditate_ticks_feed_warning_ledger(self):
        resolver = SkillResolver("SAM")
        toggle = resolver.get("Toggle buff: Meditate")
        self.assertIsNotNone(toggle)

        state = SamJobState()
        state.on_press("默想", {"potency": 0}, 0.0, 0.0)
        state.on_press_complete("默想", 0.0)
        state.on_press("Toggle buff: Meditate", toggle, 7.15, 7.15)
        state.on_press("晓风", {"amas_name": "Gyofu", "potency": 240}, 30.0, 30.0)

        self.assertEqual(state.meditation_stacks, 2)
        self.assertEqual(state.kenki, 20)

    def test_sam_75_potencies_kenki_and_ready_states(self):
        resolver = SkillResolver("SAM", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        self.assertEqual(resolver.get("Gekko")["base_potency"], 210)
        self.assertEqual(resolver.get("Tendo Goken")["potency"], 410)
        self.assertEqual(resolver.get("Tendo Kaeshi Goken")["potency"], 410)

        state = SamJobState()

        def use(name, current_time):
            skill = resolver.get(name)
            state.set_event_context({})
            press_state = state.on_press(name, skill, current_time, current_time)
            payload = {"tid": 1, "targets": 1, "is_gcd": skill.get("is_gcd"), **press_state}
            state.on_press_confirmed(name, skill, current_time, payload)
            potency, is_combo = state.resolve_potency(name, skill, current_time, payload)
            state.on_damage_resolved(name, skill, current_time, is_combo, payload)
            return potency

        state.kenki = 100
        use("Hissatsu: Shinten", 0.0)
        use("Hissatsu: Kyuten", 0.1)
        self.assertEqual(state.kenki, 50)

        state.combo_action = "Gyofu"
        state.combo_time = 0.0
        use("Yukikaze", 1.0)
        use("Enpi", 2.0)
        self.assertEqual(state.kenki, 75)

        state.kenki = 0
        state.sen = {"setsu", "getsu", "ka"}
        use("Hagakure", 3.0)
        use("Pop Tengentsu", 3.1)
        self.assertEqual(state.kenki, 40)
        self.assertEqual(state.sen, set())

        use("Ikishoten", 4.0)
        use("Ogi Namikiri", 4.1)
        use("Zanshin", 4.2)
        self.assertEqual(state.kenki, 40)

        use("Meikyo Shisui", 5.0)
        state.sen = {"setsu", "getsu"}
        use("Tendo Goken", 5.1)
        use("Tendo Kaeshi Goken", 5.2)
        self.assertFalse(state.get_resource_warnings())

    def test_sam_fuka_reduces_implicit_cast_time(self):
        resolver = SkillResolver("SAM", "7.5")
        if resolver.provider is None:
            self.skipTest("AMAS skill provider is unavailable")

        stats = dict(BASE_STATS, job="SAM")
        sim = DpsSimulator(stats, [], iterations=1)
        midare = resolver.get("Midare Setsugekka")
        speed_cast = sim.effective_cast_time(midare, {})
        state = SamJobState()
        state.shifu_until = 30.0

        self.assertEqual(speed_cast, 1.28)
        self.assertAlmostEqual(
            state.effective_cast_time("Midare Setsugekka", midare, {}, 1.0, speed_cast),
            1.1136,
        )
        self.assertEqual(
            state.effective_cast_time("Midare Setsugekka", midare, {"cast_time": 1.3}, 1.0, 1.3),
            1.3,
        )

    def test_generic_combo_state_ignores_ogcd_damage(self):
        state = JobState("TEST")
        state.on_damage_resolved("Starter", {"potency": 100, "is_gcd": True}, 0.0, False, {})
        state.on_damage_resolved("Ability", {"potency": 500, "is_gcd": False}, 1.0, False, {})
        potency, is_combo = state.resolve_potency(
            "Finisher",
            {"potency": 400, "base_potency": 100, "combo_prev": ["Starter"], "is_gcd": True},
            2.5,
            {},
        )

        self.assertTrue(is_combo)
        self.assertEqual(potency, 400)

    def test_combo_jobs_keep_chain_across_provider_ogcd_damage(self):
        cases = {
            "NIN": ("Spinning Edge", "Bhavacakra", "Gust Slash"),
            "RPR": ("Slice", "Gluttony", "Waxing Slice"),
            "DRG": ("True Thrust", "High Jump", "Spiral Blow"),
            "MCH": ("Heated Split Shot", "Gauss Round", "Heated Slug Shot"),
            "DNC": ("Cascade", "Fan Dance", "Fountain"),
            "RDM": ("Enchanted Riposte", "Fleche", "Enchanted Zwerchhau"),
            "VPR": ("Reawaken", "First Legacy", "First Generation"),
        }
        for job, (starter_name, ogcd_name, finisher_name) in cases.items():
            resolver = SkillResolver(job)
            if resolver.provider is None:
                self.skipTest("AMAS skill provider is unavailable")

            with self.subTest(job=job):
                state = create_job_state(job)
                starter = resolver.get(starter_name)
                ogcd = resolver.get(ogcd_name)
                finisher = resolver.get(finisher_name)
                self.assertTrue(starter["is_gcd"])
                self.assertFalse(ogcd["is_gcd"])
                self.assertTrue(finisher["is_gcd"])

                starter_potency, starter_combo = state.resolve_potency(starter_name, starter, 0.0, {})
                self.assertGreater(starter_potency, 0)
                state.on_damage_resolved(starter_name, starter, 0.0, starter_combo, {})

                ogcd_potency, ogcd_combo = state.resolve_potency(ogcd_name, ogcd, 1.0, {})
                self.assertGreater(ogcd_potency, 0)
                state.on_damage_resolved(ogcd_name, ogcd, 1.0, ogcd_combo, {})

                finisher_potency, finisher_combo = state.resolve_potency(finisher_name, finisher, 2.5, {})
                self.assertTrue(finisher_combo)
                self.assertEqual(finisher_potency, finisher["potency"])

    def test_sam_m12s_postman_backup_authoritative_replay(self):
        path = REPO_ROOT / "examples/skill_lines" / "sam_m9_m12s" / "m12s_postman_cn.csv"
        events, _meta = parse_axis_csv(
            path,
            normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, "SAM"),
        )
        stats = dict(BASE_STATS)
        stats["job"] = "SAM"
        sim = DpsSimulator(stats, events, iterations=1)

        with patch.object(random, "random", return_value=1.0), patch.object(
                random, "uniform", side_effect=lambda low, high: (low + high) / 2):
            total, last_hit, _dmg, counts, *_tail, resource_warnings = sim.run_one_simulation(is_first_run=True)

        self.assertAlmostEqual(total, 14328257.262634682, places=6)
        self.assertAlmostEqual(last_hit, 383.21675, places=6)
        self.assertEqual(counts["Auto Attack"], 157)
        self.assertEqual(resource_warnings, [])

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
            "RDM": [row(0.0, "Prefulgence", 116)],
            "PCT": [row(0.0, "Fanged Muse", 119)],
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
