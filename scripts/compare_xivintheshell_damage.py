import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_DIR = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from sim import (  # noqa: E402
    DpsSimulator,
    SkillResolver,
    build_skill_coverage,
    normalize_skill_name_for_job,
)
from xiv_axis_csv import parse_axis_csv  # noqa: E402
from xiv_job_data import JOB_PROFILES  # noqa: E402


LONG_JOBS = ("MNK", "DRG", "VPR", "BRD", "MCH", "DNC", "SMN", "RDM")


def match_key(value):
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


KEY_ALIASES = {
    "attack": "autoattack",
    "emyprealarrow": "empyrealarrow",
}


def canonical_key(value):
    key = match_key(value)
    return KEY_ALIASES.get(key, key)


def display_name_from_external_key(value):
    display_aliases = {
        "autoattack": "Auto Attack",
        "empyrealarrow": "Empyreal Arrow",
    }
    if value in display_aliases:
        return display_aliases[value]
    return str(value or "").replace("_", " ").title()


def external_source_key(value):
    return str(value or "").split("@", 1)[0].strip()


def load_csv_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_record(path):
    if not path or not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def stats_from_record(job, record):
    config = record.get("config", {})
    profile = JOB_PROFILES.get(job, JOB_PROFILES.get("SAM"))
    speed = config.get("spellSpeed" if profile.speed_stat == "SPS" else "skillSpeed")
    if speed is None:
        speed = config.get("skillSpeed", config.get("spellSpeed", 420))
    return {
        "job": job,
        "version": "7.5",
        "main_stat": int(config.get("main", 6498)),
        "crt": int(config.get("criticalHit", 3605)),
        "det": int(config.get("determination", 2426)),
        "dh": int(config.get("directHit", 1793)),
        "sks": int(speed),
        "wd": int(config.get("wd", 158)),
        "delay": 2.64,
    }


def aggregate_action_rows(rows):
    counts = Counter()
    first_time = {}
    last_time = {}
    for row in rows:
        action = row.get("action", "").strip()
        if not action:
            continue
        key = canonical_key(action)
        counts[key] += 1
        t = float(row.get("time") or 0)
        first_time.setdefault(key, t)
        last_time[key] = t
    return counts, first_time, last_time


def aggregate_external_damage(rows):
    events = Counter()
    potency = defaultdict(float)
    first_time = {}
    last_time = {}
    for row in rows:
        source_key = external_source_key(row.get("damageSource", ""))
        key = canonical_key(source_key)
        if not key:
            continue
        row_potency = float(row.get("potency") or 0)
        if row_potency <= 0:
            continue
        events[key] += 1
        potency[key] += row_potency
        t = float(row.get("time") or 0)
        first_time.setdefault(key, t)
        last_time[key] = t
    return events, potency, first_time, last_time


def aggregate_sim(job, axis_path, record_path):
    record = load_record(record_path)
    stats = stats_from_record(job, record)
    events, meta = parse_axis_csv(
        axis_path,
        normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job),
    )
    resolver = SkillResolver(job)
    coverage = build_skill_coverage(events, resolver, csv_meta=meta)
    random.seed(0)
    sim = DpsSimulator(stats, events, iterations=1)
    total, duration, skill_dmg, skill_count, *_rest = sim.run_one_simulation(is_first_run=True)
    target_sum = _rest[5] if len(_rest) > 5 else Counter()
    resource_warnings = _rest[8] if len(_rest) > 8 else []
    out = {}
    for name, count in skill_count.items():
        key = canonical_key(name)
        out[key] = {
            "name": name,
            "sim_count": int(count),
            "sim_target_sum": int(target_sum.get(name, 0)),
            "sim_damage_one_run": float(skill_dmg.get(name, 0.0)),
        }
    return out, coverage, total, duration, resource_warnings


def compare_one(job, axis_path, damage_path, record_path, out_dir):
    action_rows = load_csv_rows(axis_path)
    damage_rows = load_csv_rows(damage_path)
    action_counts, action_first, action_last = aggregate_action_rows(action_rows)
    damage_events, external_potency, damage_first, damage_last = aggregate_external_damage(damage_rows)
    sim_rows, coverage, sim_total, duration, resource_warnings = aggregate_sim(job, axis_path, record_path)

    all_keys = set(action_counts) | set(damage_events) | set(sim_rows)
    rows = []
    for key in sorted(all_keys):
        sim = sim_rows.get(key, {})
        name = sim.get("name") or display_name_from_external_key(key)
        rows.append({
            "job": job,
            "skill_key": key,
            "display_name": name,
            "axis_action_count": action_counts.get(key, 0),
            "sim_count": sim.get("sim_count", 0),
            "sim_target_sum": sim.get("sim_target_sum", 0),
            "sim_damage_one_run": round(sim.get("sim_damage_one_run", 0.0), 3),
            "xiv_damage_events": damage_events.get(key, 0),
            "xiv_total_potency": round(external_potency.get(key, 0.0), 6),
            "first_axis_time": action_first.get(key, ""),
            "last_axis_time": action_last.get(key, ""),
            "first_xiv_damage_time": damage_first.get(key, ""),
            "last_xiv_damage_time": damage_last.get(key, ""),
            "note": note_for_row(key, action_counts, damage_events, sim_rows),
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    job_lower = job.lower()
    csv_path = out_dir / f"{job_lower}_xivintheshell_long_skill_comparison.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["job"])
        writer.writeheader()
        writer.writerows(rows)

    warnings_path = out_dir / f"{job_lower}_resource_warnings.csv"
    warning_fields = ["job", "row_no", "time", "skill", "code", "severity", "message"]
    with open(warnings_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=warning_fields)
        writer.writeheader()
        for warning in resource_warnings:
            writer.writerow({field: warning.get(field, "") for field in warning_fields})

    summary = {
        "job": job,
        "axis": str(axis_path.relative_to(REPO_ROOT)),
        "damage": str(damage_path.relative_to(REPO_ROOT)),
        "record": str(record_path.relative_to(REPO_ROOT)) if record_path.exists() else "",
        "rows": len(rows),
        "axis_actions": sum(action_counts.values()),
        "xiv_damage_rows": sum(damage_events.values()),
        "coverage_status": coverage["status"],
        "coverage_unknown": coverage["stats"].get("unrecognized_events", 0),
        "coverage_needs_state": coverage["stats"].get("needs_state_events", 0),
        "coverage_followup": coverage["stats"].get("followup_unmodeled_events", 0),
        "sim_duration": round(duration, 3),
        "sim_total_damage_one_run": round(sim_total, 3),
        "resource_warning_count": len(resource_warnings),
        "resource_warnings_csv": str(warnings_path.relative_to(REPO_ROOT)),
        "comparison_csv": str(csv_path.relative_to(REPO_ROOT)),
    }
    return summary


def note_for_row(key, action_counts, damage_events, sim_rows):
    notes = []
    action_count = action_counts.get(key, 0)
    damage_count = damage_events.get(key, 0)
    sim = sim_rows.get(key, {})
    sim_count = sim.get("sim_count", 0)
    sim_damage = sim.get("sim_damage_one_run", 0.0)

    if action_count and not damage_count:
        if sim_count and sim_damage:
            notes.append("axis/simulator damage has no external damage key; likely reference naming or generated-damage attribution mismatch")
        elif sim_count:
            notes.append("axis/simulator zero-damage action; likely buff, step, stance, or utility")
        else:
            notes.append("axis-only zero-damage action; likely buff/utility handled outside simulator skill counts")
    if damage_count and not action_count:
        if sim_count:
            if sim_count == damage_count:
                notes.append("generated damage matched external reference without an axis press")
            else:
                notes.append("generated damage in simulator and external reference without an axis press")
        elif key == "autoattack":
            notes.append("external auto-attack damage without local simulator auto-attack rows; check auto-attack scheduling")
        else:
            notes.append("external damage-only row; likely pet/follow-up, DoT tick, or generated damage not modeled as a separate simulator skill")
    if sim_count and not action_count and not damage_count:
        notes.append("simulator-only generated row; likely generic auto-attack/DoT bucket or local attribution detail")
    if action_count and key not in sim_rows:
        notes.append("axis action not counted by simulator; likely zero-damage utility or unsupported damage path")
    if action_count and damage_count and sim_count == damage_count and action_count != damage_count:
        notes.append("generated damage matched external reference; axis press count differs because external damage rows include ticks or follow-ups")
    elif action_count and sim_count and action_count != sim_count:
        notes.append("sim count differs from axis action count")
        if damage_count and sim_count and damage_count != sim_count:
            notes.append("sim count differs from external damage event count")
        if action_count and damage_count and action_count != damage_count:
            notes.append("external damage event count differs from axis action count")
    else:
        if damage_count and sim_count and damage_count != sim_count:
            notes.append("sim count differs from external damage event count")
        if action_count and damage_count and action_count != damage_count:
            notes.append("external damage event count differs from axis action count")
    if not notes:
        notes.append("matched")
    return "; ".join(notes)


def write_markdown(summaries, out_path):
    lines = [
        "# Xivintheshell Long-Axis Skill Comparisons",
        "",
        "Generated: 2026-05-27",
        "",
        "These tables compare the local simulator's imported long-axis samples against xivintheshell action and damage exports. They are not real FFLogs validation; they are a reproducible external-detail baseline for Task I.",
        "",
        "| Job | Axis actions | XIV damage rows | Coverage | Resource warnings | Warning details | Output |",
        "| --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for item in summaries:
        warning_link = "`" + item["resource_warnings_csv"] + "`" if item.get("resource_warning_count", 0) else "-"
        lines.append(
            f"| {item['job']} | {item['axis_actions']} | {item['xiv_damage_rows']} | "
            f"{item['coverage_status']} | {item.get('resource_warning_count', 0)} | "
            f"{warning_link} | `{item['comparison_csv']}` |"
        )
    lines.extend([
        "",
        "Interpretation notes:",
        "",
        "- `axis_action_count` comes from the xivintheshell action-log CSV.",
        "- `xiv_damage_events` and `xiv_total_potency` come from the xivintheshell damage-log CSV.",
        "- `sim_damage_one_run` is one seeded local simulator run and is useful for presence/regression checks, not direct potency equality.",
        "- `Attack` from xivintheshell is normalized to local `Auto Attack`; `Emyprealarrow` is normalized to `Empyreal Arrow`.",
        "- Rows marked as damage-only are usually DoT ticks, pet hits, or follow-up damage generated by xivintheshell.",
        "- Resource warning CSVs include `row_no`, time, skill, code, severity, and message. Warnings are non-blocking and mark places where a manually arranged axis may be mechanically loose.",
    ])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_jobs():
    jobs = []
    for job in LONG_JOBS:
        job_lower = job.lower()
        directory = REPO_ROOT / "examples/skill_lines" / f"{job_lower}_xivintheshell_long"
        jobs.append((
            job,
            directory / f"{job_lower}_xivintheshell_long.csv",
            directory / f"{job_lower}_xivintheshell_damage.csv",
            directory / f"{job_lower}_xivintheshell_long.json",
        ))
    return jobs


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Compare local simulator output against xivintheshell damage exports.")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "results" / "calibration"))
    parser.add_argument("--job", choices=LONG_JOBS)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    selected = [item for item in default_jobs() if not args.job or item[0] == args.job]
    summaries = []
    for job, axis_path, damage_path, record_path in selected:
        if not axis_path.exists() or not damage_path.exists():
            raise FileNotFoundError(f"Missing axis or damage file for {job}: {axis_path}, {damage_path}")
        summaries.append(compare_one(job, axis_path, damage_path, record_path, out_dir))

    md_path = out_dir / "xivintheshell_long_skill_comparison_summary.md"
    write_markdown(summaries, md_path)
    print(str(md_path.relative_to(REPO_ROOT)))
    for item in summaries:
        print(f"{item['job']}\t{item['coverage_status']}\t{item['comparison_csv']}")


if __name__ == "__main__":
    main()
