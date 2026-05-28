import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "source"
OUT_DIR = ROOT / "data"

ACTION_CATEGORIES = {"2", "3", "4", "6", "7", "9", "15"}
JOB_COLUMNS = [
    "ADV", "GLA", "PGL", "MRD", "LNC", "ARC", "CNJ", "THM",
    "CRP", "BSM", "ARM", "GSM", "LTW", "WVR", "ALC", "CUL",
    "MIN", "BTN", "FSH", "PLD", "MNK", "WAR", "DRG", "BRD",
    "WHM", "BLM", "ACN", "SMN", "SCH", "ROG", "NIN", "MCH",
    "DRK", "AST", "SAM", "RDM", "BLU", "GNB", "DNC", "RPR",
    "SGE", "VPR", "PCT", "BST",
]


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_bool(value):
    return str(value).lower() == "true"


def read_en_csv(name):
    with open(SOURCE_DIR / f"en_{name}", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_cn_csv(name):
    with open(SOURCE_DIR / f"cn_{name}", encoding="utf-8-sig", newline="") as f:
        raw_rows = list(csv.reader(f))

    key_row = raw_rows[0]
    name_row = raw_rows[1]
    headers = []
    seen = defaultdict(int)
    for i, key in enumerate(key_row):
        header = name_row[i] if i < len(name_row) and name_row[i] else key
        if header == "#":
            header = "#"
        seen[header] += 1
        if seen[header] > 1:
            header = f"{header}__{seen[header]}"
        headers.append(header)

    return [dict(zip(headers, row)) for row in raw_rows[3:]]


def index_by_id(rows):
    return {as_int(row.get("#")): row for row in rows if str(row.get("#", "")).strip()}


def load_jobs():
    en_jobs = index_by_id(read_en_csv("ClassJob.csv"))
    cn_jobs = index_by_id(read_cn_csv("ClassJob.csv"))
    by_abbr = {}

    for job_id, en_job in en_jobs.items():
        abbr = en_job.get("Abbreviation", "")
        if not abbr:
            continue
        cn_job = cn_jobs.get(job_id, {})
        by_abbr[abbr] = {
            "id": job_id,
            "abbr": abbr,
            "en": en_job.get("NameEnglish") or en_job.get("Name") or abbr,
            "cn": cn_job.get("Name") or abbr,
        }
    return en_jobs, cn_jobs, by_abbr


def load_class_job_categories():
    rows = index_by_id(read_en_csv("ClassJobCategory.csv"))
    categories = {}
    for category_id, row in rows.items():
        jobs = [abbr for abbr in JOB_COLUMNS if row.get(abbr) == "True"]
        categories[category_id] = {
            "id": category_id,
            "name": row.get("Name", ""),
            "jobs": jobs,
        }
    return categories


def action_applies_to(action, en_jobs, class_job_categories, jobs_by_abbr):
    job_id = as_int(action.get("ClassJob"), -1)
    category_id = as_int(action.get("ClassJobCategory"), 0)

    if job_id > 0 and job_id in en_jobs:
        abbr = en_jobs[job_id].get("Abbreviation", "")
        return [abbr] if abbr else []

    if category_id > 0:
        jobs = class_job_categories.get(category_id, {}).get("jobs", [])
        return [abbr for abbr in jobs if abbr in jobs_by_abbr and abbr != "ADV"]

    return []


def is_job_skill(action, include_pvp=False):
    if not action.get("Name"):
        return False
    if action.get("ActionCategory") not in ACTION_CATEGORIES:
        return False
    if action.get("Name", "").startswith("●"):
        return False
    if not include_pvp and as_bool(action.get("IsPvP")):
        return False

    job_id = as_int(action.get("ClassJob"), -1)
    category_id = as_int(action.get("ClassJobCategory"), 0)
    level = as_int(action.get("ClassJobLevel"), 0)
    is_player = as_bool(action.get("IsPlayerAction"))
    is_role = as_bool(action.get("IsRoleAction"))

    if is_player and (job_id > 0 or category_id > 0 or is_role):
        return True
    if level > 0 and category_id > 0:
        return True
    return False


def build_rows(include_pvp=False):
    en_actions = read_en_csv("Action.csv")
    cn_actions = index_by_id(read_cn_csv("Action.csv"))
    en_categories = index_by_id(read_en_csv("ActionCategory.csv"))
    cn_categories = index_by_id(read_cn_csv("ActionCategory.csv"))
    en_jobs, _, jobs_by_abbr = load_jobs()
    class_job_categories = load_class_job_categories()

    rows = []
    for action in en_actions:
        if not is_job_skill(action, include_pvp=include_pvp):
            continue

        action_id = as_int(action.get("#"), -1)
        cn_action = cn_actions.get(action_id, {})
        cn_name = cn_action.get("Name", "")
        en_name = action.get("Name", "")
        if not cn_name or not en_name:
            continue

        category_id = as_int(action.get("ActionCategory"), 0)
        job_abbrs = action_applies_to(action, en_jobs, class_job_categories, jobs_by_abbr)
        if not job_abbrs:
            continue

        rows.append({
            "source_sheet": "Action",
            "action_id": action_id,
            "cn_name": cn_name,
            "en_name": en_name,
            "action_category_cn": cn_categories.get(category_id, {}).get("Name", ""),
            "action_category_en": en_categories.get(category_id, {}).get("Name", ""),
            "classjob_id": action.get("ClassJob", ""),
            "classjob_category_id": action.get("ClassJobCategory", ""),
            "level": action.get("ClassJobLevel", ""),
            "job_abbrs": ";".join(job_abbrs),
            "job_names_cn": ";".join(jobs_by_abbr[j]["cn"] for j in job_abbrs),
            "job_names_en": ";".join(jobs_by_abbr[j]["en"] for j in job_abbrs),
            "is_role_action": action.get("IsRoleAction", ""),
            "is_player_action": action.get("IsPlayerAction", ""),
            "is_pvp": action.get("IsPvP", ""),
        })

    rows.extend(build_craft_rows(en_categories, cn_categories, en_jobs, jobs_by_abbr, class_job_categories))

    rows.sort(key=lambda row: (
        min(jobs_by_abbr[j]["id"] for j in row["job_abbrs"].split(";")),
        as_int(row["level"]),
        row["en_name"],
        row["action_id"],
    ))
    return rows


def build_craft_rows(en_categories, cn_categories, en_jobs, jobs_by_abbr, class_job_categories):
    en_rows = read_en_csv("CraftAction.csv")
    cn_rows = index_by_id(read_cn_csv("CraftAction.csv"))
    category_id = 7
    rows = []

    for action in en_rows:
        action_id = as_int(action.get("#"), -1)
        en_name = action.get("Name", "")
        if not en_name:
            continue

        job_id = as_int(action.get("ClassJob"), -1)
        category = as_int(action.get("ClassJobCategory"), 0)
        if job_id <= 0 and category <= 0:
            continue

        cn_action = cn_rows.get(action_id, {})
        cn_name = cn_action.get("Name", "")
        if not cn_name:
            continue

        if job_id > 0 and job_id in en_jobs:
            abbr = en_jobs[job_id].get("Abbreviation", "")
            job_abbrs = [abbr] if abbr else []
        else:
            job_abbrs = class_job_categories.get(category, {}).get("jobs", [])
        job_abbrs = [abbr for abbr in job_abbrs if abbr in jobs_by_abbr and abbr in {"CRP", "BSM", "ARM", "GSM", "LTW", "WVR", "ALC", "CUL"}]
        if not job_abbrs:
            continue

        rows.append({
            "source_sheet": "CraftAction",
            "action_id": action_id,
            "cn_name": cn_name,
            "en_name": en_name,
            "action_category_cn": cn_categories.get(category_id, {}).get("Name", "制作能力"),
            "action_category_en": en_categories.get(category_id, {}).get("Name", "DoH Ability"),
            "classjob_id": action.get("ClassJob", ""),
            "classjob_category_id": action.get("ClassJobCategory", ""),
            "level": action.get("ClassJobLevel", ""),
            "job_abbrs": ";".join(job_abbrs),
            "job_names_cn": ";".join(jobs_by_abbr[j]["cn"] for j in job_abbrs),
            "job_names_en": ";".join(jobs_by_abbr[j]["en"] for j in job_abbrs),
            "is_role_action": "False",
            "is_player_action": "True",
            "is_pvp": "False",
        })

    return rows


def build_unique_mapping(full_rows):
    grouped = {}
    for row in full_rows:
        key = (row["cn_name"], row["en_name"], row["action_category_cn"], row["action_category_en"], row["is_pvp"])
        item = grouped.setdefault(key, {
            "cn_name": row["cn_name"],
            "en_name": row["en_name"],
            "action_category_cn": row["action_category_cn"],
            "action_category_en": row["action_category_en"],
            "job_abbrs": set(),
            "job_names_cn": set(),
            "job_names_en": set(),
            "levels": set(),
            "action_ids": [],
            "source_sheets": set(),
            "is_role_action": False,
            "is_pvp": row["is_pvp"],
        })
        item["job_abbrs"].update(row["job_abbrs"].split(";"))
        item["job_names_cn"].update(row["job_names_cn"].split(";"))
        item["job_names_en"].update(row["job_names_en"].split(";"))
        if row["level"]:
            item["levels"].add(row["level"])
        item["action_ids"].append(str(row["action_id"]))
        item["source_sheets"].add(row["source_sheet"])
        item["is_role_action"] = item["is_role_action"] or as_bool(row["is_role_action"])

    unique_rows = []
    for item in grouped.values():
        unique_rows.append({
            "cn_name": item["cn_name"],
            "en_name": item["en_name"],
            "action_category_cn": item["action_category_cn"],
            "action_category_en": item["action_category_en"],
            "job_abbrs": ";".join(sorted(item["job_abbrs"])),
            "job_names_cn": ";".join(sorted(item["job_names_cn"])),
            "job_names_en": ";".join(sorted(item["job_names_en"])),
            "levels": ";".join(sorted(item["levels"], key=lambda x: as_int(x))),
            "action_ids": ";".join(item["action_ids"]),
            "source_sheets": ";".join(sorted(item["source_sheets"])),
            "is_role_action": str(item["is_role_action"]),
            "is_pvp": item["is_pvp"],
        })

    unique_rows.sort(key=lambda row: (row["job_abbrs"], as_int(row["levels"].split(";")[0] if row["levels"] else "0"), row["en_name"]))
    return unique_rows


def write_csv(path, rows):
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json_maps(path, mapping_rows):
    en_to_cn = {}
    cn_to_en = {}
    for row in mapping_rows:
        en_to_cn.setdefault(row["en_name"], row["cn_name"])
        cn_to_en.setdefault(row["cn_name"], row["en_name"])
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(
            {"en_to_cn": en_to_cn, "cn_to_en": cn_to_en},
            f,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    pve_full = build_rows(include_pvp=False)
    all_full = build_rows(include_pvp=True)
    pve_mapping = build_unique_mapping(pve_full)
    all_mapping = build_unique_mapping(all_full)

    write_csv(OUT_DIR / "ff14_job_skill_en_cn.csv", pve_mapping)
    write_csv(OUT_DIR / "ff14_job_skill_en_cn_full.csv", pve_full)
    write_csv(OUT_DIR / "ff14_job_skill_en_cn_with_pvp.csv", all_mapping)
    write_json_maps(OUT_DIR / "ff14_job_skill_en_cn_map.json", pve_mapping)

    print(f"PvE unique mappings: {len(pve_mapping)}")
    print(f"PvE full action rows: {len(pve_full)}")
    print(f"PvE+PvP unique mappings: {len(all_mapping)}")
    print(f"Outputs written under {OUT_DIR}")


if __name__ == "__main__":
    main()
