import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from sim import (  # noqa: E402
    SkillResolver,
    build_skill_coverage,
    normalize_skill_name_for_job,
    skill_names_match,
)
from xiv_axis_csv import AxisCsvError, parse_axis_csv  # noqa: E402


JOB_HINTS = (
    ("NIN", ("NIN", "忍者")),
    ("RPR", ("RPR", "镰刀", "钐镰", "镰")),
    ("PCT", ("PCT", "绘灵", "画家", "减色")),
    ("SAM", ("SAM", "武士", "M9S", "M10S", "M11S", "M12S")),
    ("MNK", ("MNK", "武僧")),
    ("DRG", ("DRG", "龙骑")),
    ("VPR", ("VPR", "蝰蛇")),
    ("BRD", ("BRD", "诗人", "吟游")),
    ("MCH", ("MCH", "机工")),
    ("DNC", ("DNC", "舞者")),
    ("BLM", ("BLM", "黑魔")),
    ("SMN", ("SMN", "召唤")),
    ("RDM", ("RDM", "赤魔")),
)

CONTENT_JOB_HINTS = (
    ("BLM", (
        "Fire 4", "Fire IV", "High Thunder", "Flare Star", "Xenoglossy", "Umbral Soul", "Foul",
        "炽炎", "爆炎", "高闪雷", "高震雷", "耀星", "异言", "灵极魂", "秽浊", "黑魔纹",
    )),
    ("NIN", ("Fuma Shuriken", "Raiton", "Suiton", "Ten Chi Jin", "Bhavacakra")),
    ("RPR", ("Enshroud", "Communio", "Perfectio", "Arcane Circle", "Soul Slice")),
    ("PCT", ("Rainbow Drip", "Pom Muse", "Starry Muse", "Subtractive Palette", "Hammer Motif")),
    ("SAM", ("Hakaze", "Midare Setsugekka", "Higanbana", "Ogi Namikiri", "Meikyo Shisui")),
)


def is_known_non_axis_csv(path):
    name = path.name.lower()
    return name.endswith("_xivintheshell_damage.csv") or name.endswith("_skill_comparison.csv")


def infer_job(path):
    try:
        sample = path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        sample = ""
    for job, hints in CONTENT_JOB_HINTS:
        if sum(1 for hint in hints if hint in sample) >= 2:
            return job

    text = str(path).upper()
    raw_text = str(path)
    for job, hints in JOB_HINTS:
        for hint in hints:
            if hint.upper() in text or hint in raw_text:
                return job
    return "SAM"


def load_target_actions(csv_path):
    candidates = [
        csv_path.with_suffix(".txt"),
        csv_path.with_suffix(".json"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            actions = [x for x in data.get("actions", []) if x.get("type") == "Skill"]
            if actions:
                return candidate, actions
        except Exception:
            continue
    return None, []


def attach_target_counts(events, actions, job):
    final = []
    txt_idx = 0
    search_window = 15
    for row in events:
        raw_name = row.get("raw_name", row["name"])
        sim_name = row["name"]
        target_count = 1
        target_source = "default"
        if actions:
            for i in range(txt_idx, min(txt_idx + search_window, len(actions))):
                item = actions[i]
                txt_name = item.get("skillName", "")
                if skill_names_match(raw_name, sim_name, txt_name, job):
                    if "targetList" in item:
                        target_count = len(item["targetList"])
                    else:
                        target_count = item.get("targetCount", 1)
                    txt_idx = i + 1
                    target_source = "txt"
                    break
        out = dict(row)
        out["targets"] = int(target_count)
        out["target_source"] = target_source
        final.append(out)
    return final


def scan_file(path, job):
    events, meta = parse_axis_csv(
        path,
        normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job),
    )
    target_path, actions = load_target_actions(path)
    events = attach_target_counts(events, actions, job)
    if target_path:
        meta = dict(meta)
        meta["target_file"] = str(target_path)
    return build_skill_coverage(events, SkillResolver(job), csv_meta=meta)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Scan XIV in the Shell CSV skill coverage.")
    parser.add_argument("paths", nargs="*", default=[str(REPO_ROOT / "examples/skill_lines")])
    parser.add_argument("--job", choices=tuple(job for job, _ in JOB_HINTS), help="Force one job for all files.")
    parser.add_argument("--issues-only", action="store_true", help="Only print files with unknown/state/follow-up issues.")
    parser.add_argument("--show-skills", action="store_true", help="Print per-file problematic skill names.")
    parser.add_argument("--include-non-axis", action="store_true", help="Also scan known non-axis CSV exports such as damage logs.")
    args = parser.parse_args()

    csv_paths = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if path.is_dir():
            for csv_path in sorted(path.rglob("*.csv")):
                if not args.include_non_axis and is_known_non_axis_csv(csv_path):
                    continue
                csv_paths.append(csv_path)
        else:
            csv_paths.append(path)

    print("file\tjob\trows\tunique\tunknown\tneeds_state\tfollowup\tstatus")
    failures = 0
    for path in csv_paths:
        job = args.job or infer_job(path)
        rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        try:
            report = scan_file(path, job)
            stats = report["stats"]
            has_issue = (
                stats.get("unrecognized_events", 0)
                or stats.get("needs_state_events", 0)
                or stats.get("followup_unmodeled_events", 0)
            )
            if args.issues_only and not has_issue:
                continue
            print(
                f"{rel}\t{job}\t{stats.get('total_events', 0)}\t{stats.get('unique_skills', 0)}\t"
                f"{stats.get('unrecognized_events', 0)}\t{stats.get('needs_state_events', 0)}\t"
                f"{stats.get('followup_unmodeled_events', 0)}\t{report['status']}"
            )
            if args.show_skills and has_issue:
                problem_rows = [
                    row for row in report["rows"]
                    if row["classification"]["category"] == "unrecognized"
                    or row["classification"]["needs_state"]
                    or row["classification"]["followup_unmodeled"]
                ]
                for row in problem_rows:
                    cls = row["classification"]
                    print(f"  - {row['name']} x{row['count']}: {cls['category_label']} | {row['tags_text']} | {cls['reason']}")
        except AxisCsvError as exc:
            failures += 1
            print(f"{rel}\t{job}\tERROR\t-\t-\t-\t-\t{exc}")
        except Exception as exc:
            failures += 1
            print(f"{rel}\t{job}\tERROR\t-\t-\t-\t-\t{type(exc).__name__}: {exc}")

    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
