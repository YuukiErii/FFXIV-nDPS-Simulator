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
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SIM_SRC = REPO_ROOT / "src" / "ffxiv_ndps_simulator"
if str(SIM_SRC) not in sys.path:
    sys.path.insert(0, str(SIM_SRC))

from sim import (  # noqa: E402
    DpsSimulator,
    JOB_PROFILES,
    SkillResolver,
    build_skill_coverage,
    normalize_skill_name_for_job,
    parse_axis_csv,
    skill_names_match,
)


DEFAULT_STATS = {
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "delay": 2.64,
    "party_bonus": 1.05,
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _target_actions(path: Path | None) -> list[dict]:
    if not path:
        return []
    payload = _load_json(path)
    return [item for item in payload.get("actions", []) if item.get("type") == "Skill"]


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
        for index in range(txt_idx, min(txt_idx + search_window, max_txt)):
            txt_item = target_actions[index]
            txt_name = txt_item.get("skillName", "")
            if skill_names_match(raw_name, row["name"], txt_name, job):
                target_count = len(txt_item.get("targetList", [])) if "targetList" in txt_item else txt_item.get("targetCount", 1)
                target_source = "txt"
                txt_idx = index + 1
                break
        row["targets"] = int(target_count)
        row["target_source"] = target_source
        out.append(row)
    return out


def _parse_windows(value: str | None) -> list[tuple[float, float]]:
    if not value:
        return []
    windows = []
    for chunk in value.replace("，", ",").split(","):
        text = chunk.strip().replace("(", "").replace(")", "")
        if not text or "-" not in text:
            continue
        start, end = text.split("-", 1)
        windows.append((float(start), float(end)))
    return windows


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


def run(payload: dict) -> dict:
    job = payload.get("job", "SAM")
    csv_path = Path(payload["csv_path"]).expanduser().resolve()
    target_path = Path(payload["target_path"]).expanduser().resolve() if payload.get("target_path") else None
    iterations = int(payload.get("iterations", 1000))
    threshold = float(payload.get("threshold", 0.0))
    seed = int(payload.get("seed") or random.randrange(1, 2**31))
    random.seed(seed)

    stats = dict(DEFAULT_STATS)
    stats.update(payload.get("stats", {}))
    profile = JOB_PROFILES.get(job, JOB_PROFILES["SAM"])
    stats["job"] = job
    stats["main_stat"] = int(stats.get("main_stat", stats.get("str", DEFAULT_STATS["main_stat"])))
    stats["str"] = stats["main_stat"]
    stats["party_bonus"] = float(stats.get("party_bonus", profile.party_bonus))

    events, csv_meta = parse_axis_csv(csv_path, normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job))
    events = _attach_targets(events, _target_actions(target_path), job)
    coverage = build_skill_coverage(events, SkillResolver(job), csv_meta=csv_meta)

    sim = DpsSimulator(
        stats,
        events,
        iterations=iterations,
        global_downtime_list=_parse_windows(payload.get("global_downtime")),
        custom_snaps=[float(value) for value in payload.get("custom_snaps", [])],
    )
    dps_list, duration, last_hit, stats_pkg, log = sim.run_batch(threshold=threshold)
    mean_dps = statistics.mean(dps_list)
    std_dps = statistics.stdev(dps_list) if iterations > 1 else 0.0
    base_gcd, job_gcd = DpsSimulator.calculate_gcd(int(stats["sks"]), job)

    return {
        "metadata": {
            "job": job,
            "csv_path": str(csv_path),
            "target_path": str(target_path) if target_path else "",
            "csv_format": csv_meta.get("format", ""),
            "iterations": iterations,
            "seed": seed,
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
        },
        "coverage": {
            "status": coverage.get("status"),
            "stats": _json_safe(coverage.get("stats")),
            "rows": _json_safe(coverage.get("rows", [])[:500]),
        },
        "skills": _skill_rows(stats_pkg, sim, iterations),
        "combat_log": log[:1000],
        "distribution": _distribution(dps_list),
        "resource_warnings": stats_pkg.get("resource_warnings", []),
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
