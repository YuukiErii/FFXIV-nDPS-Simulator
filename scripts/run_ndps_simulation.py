#!/usr/bin/env python
"""Run the personal nDPS simulator as a JSON backend for the modern UI."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SIM_SRC = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIM_SRC) not in sys.path:
    sys.path.insert(0, str(SIM_SRC))

from sim import (  # noqa: E402
    APP_TITLE,
    DpsSimulator,
    JOB_PROFILES,
    PERSONAL_NDPS_DEFINITION,
    SkillResolver,
    build_skill_coverage,
    normalize_skill_name_for_job,
    parse_axis_csv,
    skill_names_match,
)
from xiv_sim_core import parse_downtime_windows, parse_marker_track_downtime_windows  # noqa: E402
from xiv_job_data import DEFAULT_MAIN_STATS, DEFAULT_WEAPON_DELAYS  # noqa: E402


DEFAULT_STATS = {
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "delay": 2.64,
    "party_bonus": 1.05,
    "version": "7.5",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _target_record(path: Path | None) -> dict:
    if not path:
        return {}
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_text": text}


def _target_record_downtime(record: dict) -> list[tuple[float, float]]:
    return parse_marker_track_downtime_windows(record) or parse_downtime_windows(record.get("_text", ""))


def _attach_targets(events: list[dict], target_actions: list[dict], job: str) -> list[dict]:
    if not target_actions:
        return [dict(event, targets=int(event.get("targets", 1)), target_source="default") for event in events]

    out = []
    txt_idx = 0
    search_window = 15
    max_txt = len(target_actions)
    for event in events:
        row = dict(event)
        raw_name = row.get("raw_name", row["name"])
        target_count = 1
        target_source = "default"
        target_ids = []
        for index in range(txt_idx, min(txt_idx + search_window, max_txt)):
            txt_item = target_actions[index]
            txt_name = txt_item.get("skillName", "")
            if skill_names_match(raw_name, row["name"], txt_name, job):
                if "targetList" in txt_item:
                    target_ids = list(txt_item.get("targetList", []))
                    target_count = len(target_ids)
                else:
                    target_count = txt_item.get("targetCount", 1)
                target_source = "txt"
                txt_idx = index + 1
                break
        row["targets"] = int(target_count)
        if target_ids:
            row["target_ids"] = target_ids
        row["target_source"] = target_source
        out.append(row)
    return out


def _parse_windows(value) -> list[tuple[float, float]]:
    return parse_downtime_windows(value)
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        windows = []
        for item in value:
            if isinstance(item, dict):
                start = item.get("start")
                end = item.get("end")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                start, end = item[0], item[1]
            else:
                continue
            windows.append((float(start), float(end)))
        return windows
    value = str(value).replace("，", ",")
    windows = []
    for chunk in value.replace("，", ",").split(","):
        text = chunk.strip().replace("(", "").replace(")", "")
        if not text or "-" not in text:
            continue
        start, end = text.split("-", 1)
        windows.append((float(start), float(end)))
    return windows


def _parse_target_downtime(value) -> dict[int, list[tuple[float, float]]]:
    if not value:
        return {}
    if isinstance(value, dict):
        return {
            int(target_id): parsed
            for target_id, windows in value.items()
            if (parsed := _parse_windows(windows))
        }
    out = {}
    for line in str(value).replace("；", ";").split(";"):
        if ":" not in line:
            continue
        target_id, windows = line.split(":", 1)
        target_id = target_id.strip().upper().removeprefix("T").strip()
        if target_id.isdigit():
            parsed = _parse_windows(windows)
            if parsed:
                out[int(target_id)] = parsed
    return out


def _intersect_two_windows(left: list[tuple[float, float]], right: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            start = max(left_start, right_start)
            end = min(left_end, right_end)
            if start < end:
                out.append((start, end))
    return out


def _downtime_intersection(downtime_config: dict[int, list[tuple[float, float]]]) -> list[tuple[float, float]]:
    configs = [windows for _, windows in sorted(downtime_config.items()) if windows]
    if not configs:
        return []
    intersection = configs[0]
    for windows in configs[1:]:
        intersection = _intersect_two_windows(intersection, windows)
        if not intersection:
            break
    return intersection


def _parse_dot_config(value, job: str) -> dict[str, list[int]]:
    if not value:
        return {}
    raw = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            raw = {}
            for line in text.replace("；", ";").split(";"):
                if ":" not in line:
                    continue
                name, targets = line.split(":", 1)
                ids = [
                    int(item.strip().upper().removeprefix("T"))
                    for item in targets.split(",")
                    if item.strip().upper().removeprefix("T").isdigit()
                ]
                if ids:
                    raw[name.strip()] = ids
    if not isinstance(raw, dict):
        return {}
    return {
        normalize_skill_name_for_job(str(name).strip(), job): [int(target_id) for target_id in targets]
        for name, targets in raw.items()
        if str(name).strip() and isinstance(targets, (list, tuple))
    }


def _skill_rows(stats_pkg: dict, sim: DpsSimulator, iterations: int) -> list[dict]:
    rows = []
    s_dps = stats_pkg["dps"]
    s_count = stats_pkg["count"]
    target_stats = stats_pkg.get("target_stats", {})
    agg_count = stats_pkg["agg_count"]
    agg_crit = stats_pkg["agg_crit"]
    agg_dh = stats_pkg["agg_dh"]
    agg_cdh = stats_pkg["agg_cdh"]

    for skill in sorted(s_dps.keys(), key=lambda item: statistics.mean(s_dps[item]), reverse=True):
        avg_count = statistics.mean(s_count[skill])
        total_hits = target_stats.get(skill, 0)
        hit_count = agg_count[skill]
        rows.append(
            {
                "skill": skill,
                "avg_cast_count": round(avg_count, 3),
                "avg_hits_per_cast": round(total_hits / avg_count if avg_count > 0 else 0.0, 3),
                "avg_dps": round(statistics.mean(s_dps[skill]), 6),
                "std_dps": round(statistics.stdev(s_dps[skill]) if iterations > 1 else 0.0, 6),
                "total_hit_events": int(hit_count),
                "crit_percent": round(agg_crit[skill] / hit_count * 100, 3) if hit_count else 0.0,
                "direct_hit_percent": round(agg_dh[skill] / hit_count * 100, 3) if hit_count else 0.0,
                "crit_direct_percent": round(agg_cdh[skill] / hit_count * 100, 3) if hit_count else 0.0,
                "known_skill": bool(sim.get_skill(skill)),
            }
        )
    return rows


def _total_skill_row(stats_pkg: dict, mean_dps: float, std_dps: float, iterations: int) -> dict:
    total_hits = stats_pkg.get("total_hits_list", [])
    return {
        "skill": "--- TOTAL ---",
        "avg_cast_count": round(statistics.mean(total_hits), 3) if total_hits else 0.0,
        "std_cast_count": round(statistics.stdev(total_hits), 3) if len(total_hits) > 1 else 0.0,
        "avg_hits_per_cast": 0.0,
        "avg_dps": round(mean_dps, 6),
        "std_dps": round(std_dps if iterations > 1 else 0.0, 6),
        "total_hit_events": int(sum(total_hits)) if total_hits else 0,
        "crit_percent": 0.0,
        "direct_hit_percent": 0.0,
        "crit_direct_percent": 0.0,
        "known_skill": True,
    }


def _best_run_rows(stats_pkg: dict, sim: DpsSimulator) -> list[dict]:
    best = stats_pkg.get("best_run") or {}
    if not best:
        return []
    rows = []
    for skill in sorted(best["dmg"].keys(), key=lambda item: best["dmg"][item], reverse=True):
        count = best["count"][skill]
        if count <= 0:
            continue
        skill_data = sim.get_skill(skill)
        is_damage = skill_data is None or skill_data.get("potency", 0) > 0 or skill_data.get("dot_potency", 0) > 0
        rows.append(
            {
                "skill": skill,
                "count": int(count),
                "hits": int(best["targets"][skill]),
                "damage": round(best["dmg"][skill], 3),
                "crit_percent": round(best["crit"][skill] / count * 100, 3) if is_damage else None,
                "direct_hit_percent": round(best["dh"][skill] / count * 100, 3) if is_damage else None,
                "crit_direct_percent": round(best["cdh"][skill] / count * 100, 3) if is_damage else None,
            }
        )
    return rows


def _interval_rows(stats_pkg: dict, sim: DpsSimulator) -> list[dict]:
    rows = []
    for time_point in sorted((stats_pkg.get("interval_data") or {}).keys()):
        damages = stats_pkg["interval_data"][time_point]
        if not damages:
            continue
        effective_duration = sim.get_effective_duration(time_point)
        rds = [damage / effective_duration for damage in damages]
        mean_rd = statistics.mean(rds)
        std_rd = statistics.stdev(rds) if len(rds) > 1 else 0.0
        rows.append(
            {
                "time": float(time_point),
                "effective_duration": round(effective_duration, 6),
                "mean_rd": round(mean_rd, 6),
                "std_rd": round(std_rd, 6),
                "max_rd": round(max(rds), 6),
                "top_1": round(mean_rd + 2.326 * std_rd, 6),
                "top_0_1": round(mean_rd + 3.09 * std_rd, 6),
            }
        )
    return rows


def _high_run_rows(stats_pkg: dict) -> list[dict]:
    return [
        {"run_id": int(run_id), "rd": round(item["rd"], 6), "duration": round(item["dur"], 6)}
        for run_id, item in sorted(
            (stats_pkg.get("high_rd_runs") or {}).items(),
            key=lambda pair: pair[1]["rd"],
            reverse=True,
        )
    ]


def _distribution(values: list[float], step: int = 100) -> list[dict]:
    if not values:
        return []
    buckets = defaultdict(int)
    for value in values:
        buckets[math.floor(value / step) * step] += 1
    total = len(values)
    return [
        {
            "range": f"{bucket}-{bucket + step}",
            "count": buckets[bucket],
            "percent_ge": round(sum(count for key, count in buckets.items() if key >= bucket) / total * 100, 3),
        }
        for bucket in range(min(buckets), max(buckets) + step, step)
        if buckets[bucket] > 0
    ]


def _json_safe(value):
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _target_source_label(target_path: Path | None, coverage: dict) -> str:
    if target_path:
        return f"{target_path.name} (TXT/JSON target list)"
    stats = coverage.get("stats", {})
    default_events = int(stats.get("default_target_events", 0) or 0)
    total_events = int(stats.get("total_events", 0) or 0)
    if default_events:
        return f"default target=1 for {default_events}/{total_events} rows"
    return "axis target metadata"


def _evidence_status(coverage: dict, events: list[dict], csv_path: Path, resource_warnings: list[dict]) -> dict:
    stats = coverage.get("stats", {})
    coverage_ok = (
        int(stats.get("unrecognized_events", 0) or 0) == 0
        and int(stats.get("needs_state_events", 0) or 0) == 0
        and int(stats.get("followup_unmodeled_events", 0) or 0) == 0
    )
    mechanic = (
        "partial: xivintheshell damage baseline present"
        if any(path.name.endswith("_xivintheshell_damage.csv") for path in csv_path.parent.glob("*"))
        else "not established"
    )
    if resource_warnings:
        mechanic += "; resource warnings need review"
    return {
        "import_smoke_passed": "yes" if coverage_ok and events else "no",
        "mechanic_calibrated": mechanic,
        "log_validated": "no: requires real log / AMAS / audited external evidence",
    }


def run(payload: dict) -> dict:
    job = payload.get("job", "SAM")
    csv_path = Path(payload["csv_path"]).expanduser().resolve()
    target_path = Path(payload["target_path"]).expanduser().resolve() if payload.get("target_path") else None
    downtime_track_path = (
        Path(payload["downtime_track_path"]).expanduser().resolve()
        if payload.get("downtime_track_path")
        else None
    )
    iterations = int(payload.get("iterations", 1000))
    threshold = float(payload.get("threshold", 0.0))
    seed = int(payload.get("seed") or random.randrange(1, 2**31))
    random.seed(seed)

    payload_stats = payload.get("stats", {})
    stats = dict(DEFAULT_STATS)
    stats.update(payload_stats)
    if "main_stat" not in payload_stats and "str" not in payload_stats:
        stats["main_stat"] = DEFAULT_MAIN_STATS.get(job, DEFAULT_STATS["main_stat"])
    if "delay" not in payload_stats:
        stats["delay"] = DEFAULT_WEAPON_DELAYS.get(job, DEFAULT_STATS["delay"])
    profile = JOB_PROFILES.get(job, JOB_PROFILES["SAM"])
    stats["job"] = job
    stats["version"] = str(stats.get("version", DEFAULT_STATS["version"]))
    stats["main_stat"] = int(stats.get("main_stat", stats.get("str", DEFAULT_STATS["main_stat"])))
    stats["str"] = stats["main_stat"]
    stats["party_bonus"] = float(stats.get("party_bonus", profile.party_bonus))

    events, csv_meta = parse_axis_csv(csv_path, normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job))
    target_record = _target_record(target_path)
    downtime_track_record = _target_record(downtime_track_path)
    events = _attach_targets(
        events,
        [item for item in target_record.get("actions", []) if item.get("type") == "Skill"],
        job,
    )
    coverage = build_skill_coverage(events, SkillResolver(job, stats["version"]), csv_meta=csv_meta)
    multi_boss_mode = bool(payload.get("multi_boss_mode"))
    downtime_config = _parse_target_downtime(payload.get("downtime_config"))
    global_downtime = _parse_windows(payload.get("global_downtime"))
    global_downtime_source = "manual" if global_downtime else ""
    if not global_downtime:
        global_downtime = _target_record_downtime(downtime_track_record)
        if global_downtime:
            global_downtime_source = "downtime_track_path"
    if not global_downtime:
        global_downtime = _target_record_downtime(target_record)
        if global_downtime:
            global_downtime_source = "target_path_marker_track"
    if multi_boss_mode and downtime_config and not global_downtime:
        global_downtime = _downtime_intersection(downtime_config)
        global_downtime_source = "target_downtime_intersection"

    sim = DpsSimulator(
        stats,
        events,
        iterations=iterations,
        downtime_config=downtime_config,
        dot_config=_parse_dot_config(payload.get("dot_config"), job),
        multi_boss_mode=multi_boss_mode,
        global_downtime_list=global_downtime,
        custom_snaps=[float(value) for value in payload.get("custom_snaps", [])],
    )
    dps_list, duration, last_hit, stats_pkg, log = sim.run_batch(threshold=threshold)
    mean_dps = statistics.mean(dps_list)
    std_dps = statistics.stdev(dps_list) if iterations > 1 else 0.0
    base_gcd, job_gcd = DpsSimulator.calculate_gcd(int(stats["sks"]), job)
    resource_warnings = stats_pkg.get("resource_warnings", [])
    evidence = _evidence_status(coverage, events, csv_path, resource_warnings)
    skill_rows = _skill_rows(stats_pkg, sim, iterations)
    total_skill_row = _total_skill_row(stats_pkg, mean_dps, std_dps, iterations)
    high_run_rows = _high_run_rows(stats_pkg)
    provider = "ama_xiv_combat_sim local provider" if getattr(sim.skill_resolver, "provider", None) else "local fallback skill table"
    resource_status = (
        f"{len(resource_warnings)} warning(s); trend-only interpretation"
        if resource_warnings
        else "no resource warnings"
    )
    mode = "multi-boss intersection" if multi_boss_mode else "single target / manual downtime"

    return {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app": APP_TITLE,
            "job": job,
            "job_label": f"{sim.job_profile.name} ({sim.job})",
            "csv_path": str(csv_path),
            "target_path": str(target_path) if target_path else "",
            "downtime_track_path": str(downtime_track_path) if downtime_track_path else "",
            "sample_path": str(csv_path),
            "target_source": _target_source_label(target_path, coverage),
            "csv_format": csv_meta.get("format", ""),
            "iterations": iterations,
            "seed": seed,
            "game_version": stats["version"],
            "skill_data_source": provider,
            "weapon_delay": stats["delay"],
            "base_gcd": base_gcd,
            "job_gcd": job_gcd,
            "multi_boss_mode": multi_boss_mode,
            "mode": mode,
            "global_downtime": global_downtime,
            "global_downtime_count": len(global_downtime),
            "global_downtime_source": global_downtime_source,
            "downtime_config": downtime_config,
            "coverage_status": coverage.get("status"),
            "resource_status": resource_status,
            **evidence,
        },
        "definition": PERSONAL_NDPS_DEFINITION,
        "panel": {
            "job": sim.job,
            "job_name": sim.job_profile.name,
            "main_stat_name": sim.job_profile.main_stat,
            "main_stat": sim.base_main,
            "weapon_damage": int(sim.stats["wd"]),
            "speed_stat_name": sim.job_profile.speed_stat,
            "speed": int(sim.stats["sks"]),
            "crit": int(sim.stats["crt"]),
            "crit_rate": sim.crit_rate,
            "crit_damage": sim.crit_dmg,
            "direct_hit": int(sim.stats["dh"]),
            "direct_hit_rate": sim.dh_rate,
            "determination": int(sim.stats["det"]),
            "party_bonus": float(sim.stats.get("party_bonus", 1.0)),
            "weapon_delay": float(sim.stats["delay"]),
            "base_gcd": base_gcd,
            "job_gcd": job_gcd,
        },
        "summary": {
            "expected_dps": mean_dps,
            "std_dps": std_dps,
            "max_dps": max(dps_list),
            "min_dps": min(dps_list),
            "duration": duration,
            "last_hit": last_hit,
            "top_1": mean_dps + 2.326 * std_dps,
            "top_0_1": mean_dps + 3.09 * std_dps,
            "top_0_01": mean_dps + 3.719 * std_dps,
            "bottom_1": mean_dps - 2.326 * std_dps,
            "high_rd_run_count": len(high_run_rows),
        },
        "coverage": {
            "status": coverage.get("status"),
            "stats": _json_safe(coverage.get("stats")),
            "rows": _json_safe(coverage.get("rows", [])[:500]),
        },
        "skills": skill_rows,
        "skill_total": total_skill_row,
        "best_run": _best_run_rows(stats_pkg, sim),
        "intervals": _interval_rows(stats_pkg, sim),
        "high_rd_runs": high_run_rows,
        "combat_log": log,
        "distribution": _distribution(dps_list),
        "resource_warnings": resource_warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON payload path")
    parser.add_argument("--output", help="optional JSON output path")
    args = parser.parse_args()

    payload = _load_json(Path(args.input))
    result = run(payload)
    text = json.dumps(result, ensure_ascii=True, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
