import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_DIR = REPO_ROOT / "artifacts" / "calibration"
DEFAULT_OUT = REPO_ROOT / "docs" / "task_i_xivintheshell_comparison_audit.md"
JOBS = ("MNK", "DRG", "VPR", "BRD", "MCH", "DNC", "SMN", "RDM")


JOB_INTERPRETATION = {
    "MNK": (
        "Most direct skills are present. The remaining high-priority checks are Masterful Blitz / Fire's Reply "
        "xivintheshell attribution, auto-attack count drift, and keeping Tincture as a utility action rather than a "
        "missing damage event. Chakra spend rows are now surfaced as warning-only legality notes because this "
        "manual axis does not carry deterministic chakra proc evidence."
    ),
    "DRG": (
        "Core jump and Life of the Dragon actions are present. Chaotic Spring DoT ticks are now source-attributed "
        "rather than reported through a generic Dot Tick bucket; remaining checks are Wyrmwind Thrust xivintheshell "
        "attribution, Drakesbane count semantics, Firstminds' Focus assumptions, and auto-attack timing."
    ),
    "VPR": (
        "This is the cleanest long-axis comparison. Direct VPR actions match; remaining rows are auto-attack count "
        "drift plus utility / movement / tincture rows. The one resource warning marks a Rattling Coil assumption "
        "for Uncoiled Fury."
    ),
    "BRD": (
        "Direct attacks mostly exist. Caustic Bite / Stormbite / Iron Jaws DoT tick counts now match the external "
        "damage rows, and later Iron Jaws presses without both DoTs active surface resource warnings instead of "
        "refreshing phantom DoTs. Remaining checks are count deltas on Apex Arrow / Radiant Encore and auto-attack "
        "timing."
    ),
    "MCH": (
        "Main weaponskills are present. Automaton Queen now emits Armpunch / Pilebunker / Crowned Collider as "
        "separate local follow-up rows matching the external event counts, Detonator is treated as a zero-damage "
        "control row, and Wildfire matches after zero-potency external rows are excluded. Remaining check is "
        "Heat Blast's missing external damage key in this xivintheshell export."
    ),
    "DNC": (
        "Most direct skills are present and dance-step rows are expected utility. Finishing Move lacks an external "
        "damage key in this export, and Fan Dance / Last Dance / Starfall Dance count deltas need xivintheshell review. "
        "Fan Dance and Saber Dance warning rows document proc / Esprit assumptions in the manual axis."
    ),
    "SMN": (
        "SMN pet and demi generated rows are now attributed to explicit follow-up names, and Slipstream ticks are "
        "source-attributed. Resource warnings now show that the manually extended long axis contains summon/gem "
        "legality issues; the largest remaining differences are generated-hit counts for those questionable segments."
    ),
    "RDM": (
        "Direct cast and melee-chain skills are mostly aligned. RDM now emits caster auto-attack rows after the "
        "enchanted melee chain starts; the remaining issue is timing/count overrun versus xivintheshell's melee-range "
        "auto-attack windows."
    ),
}


CLASS_LABELS = {
    "matched": "Matched",
    "generated_matched": "Generated matched",
    "expected_zero_or_utility": "Expected zero / utility",
    "generated_count_delta": "Generated count delta",
    "count_delta": "Pressed-skill count delta",
    "external_generated_missing": "External generated damage gap",
    "auto_attack_gap": "Auto-attack timing/model gap",
    "sim_damage_missing_external_key": "Local damage without external key",
    "simulator_generated_only": "Simulator-only generated row",
    "known_xivintheshell_gap": "Known xivintheshell export gap",
    "review": "Needs review",
}


def load_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_warning_rows(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("code") or row.get("message")]


def as_int(value):
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def as_float(value):
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def classify(row):
    note = row.get("note", "")
    action_count = as_int(row.get("axis_action_count"))
    sim_count = as_int(row.get("sim_count"))
    damage_count = as_int(row.get("xiv_damage_events"))

    if note == "matched":
        return "matched"
    if "generated damage matched external xivintheshell" in note:
        return "generated_matched"
    if "zero-damage" in note or "utility" in note and damage_count == 0 and as_float(row.get("sim_damage_one_run")) == 0:
        return "expected_zero_or_utility"
    if row.get("job") == "MCH" and row.get("skill_key") == "heatblast" and "no external damage key" in note:
        return "known_xivintheshell_gap"
    if "external auto-attack damage" in note:
        return "auto_attack_gap"
    if "external damage-only" in note:
        return "external_generated_missing"
    if "no external damage key" in note:
        return "sim_damage_missing_external_key"
    if "simulator-only generated row" in note:
        return "simulator_generated_only"
    if "count differs" in note:
        if action_count == 0 and sim_count and damage_count:
            return "generated_count_delta"
        return "count_delta"
    return "review"


def priority_for(audit_class):
    if audit_class in {"external_generated_missing", "sim_damage_missing_external_key", "auto_attack_gap"}:
        return "P1"
    if audit_class in {"count_delta", "generated_count_delta", "simulator_generated_only", "known_xivintheshell_gap"}:
        return "P2"
    if audit_class == "expected_zero_or_utility":
        return "P3"
    return "-"


def format_link(path):
    return str(path.relative_to(REPO_ROOT)).replace("/", "\\")


def row_table(rows, include_expected=False):
    selected = []
    for row in rows:
        audit_class = row["audit_class"]
        if audit_class in {"matched", "generated_matched"}:
            continue
        if audit_class == "expected_zero_or_utility" and not include_expected:
            continue
        selected.append(row)
    if not selected:
        return ["No review rows."]

    lines = [
        "| Priority | Skill | Axis | Sim | External | XIV potency | Class | Note |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in selected:
        note = row.get("note", "").replace("|", "/")
        lines.append(
            f"| {priority_for(row['audit_class'])} | {row.get('display_name', '')} | "
            f"{as_int(row.get('axis_action_count'))} | {as_int(row.get('sim_count'))} | "
            f"{as_int(row.get('xiv_damage_events'))} | {as_float(row.get('xiv_total_potency')):.3f} | "
            f"{CLASS_LABELS.get(row['audit_class'], row['audit_class'])} | {note} |"
        )
    return lines


def warning_lines(rows):
    if not rows:
        return ["None."]
    lines = []
    for row in rows[:10]:
        row_no = row.get("row_no") or "-"
        time = row.get("time") or "-"
        skill = row.get("skill") or "-"
        code = row.get("code") or "warning"
        message = (row.get("message") or "").replace("|", "/")
        lines.append(f"- row {row_no}, {time}s, `{skill}`: `{code}` - {message}")
    if len(rows) > 10:
        lines.append(f"- ... {len(rows) - 10} more warnings in the resource warning CSV.")
    return lines


def warning_link(path):
    return str(path.relative_to(REPO_ROOT)).replace("/", "\\")


def main():
    parser = argparse.ArgumentParser(description="Generate a Task I audit report from xivintheshell comparison CSVs.")
    parser.add_argument("--comparison-dir", default=str(CALIBRATION_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    comparison_dir = Path(args.comparison_dir)
    if not comparison_dir.is_absolute():
        comparison_dir = REPO_ROOT / comparison_dir
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path

    per_job = {}
    for job in JOBS:
        path = comparison_dir / f"{job}_xivintheshell_long_skill_comparison.csv"
        rows = load_rows(path)
        for row in rows:
            row["audit_class"] = classify(row)
        warning_path = comparison_dir / f"{job}_resource_warnings.csv"
        per_job[job] = (path, rows, warning_path, load_warning_rows(warning_path))

    lines = [
        "# Task I Xivintheshell Comparison Audit",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "This audit reads the per-skill comparison CSVs generated by `scripts/compare_xivintheshell_damage.py`.",
        "It is a calibration triage artifact, not a claim of numerical validation against FFLogs or AMAS.",
        "",
        "## Summary",
        "",
        "| Job | Rows | Matched | P1 rows | P2 rows | Expected utility | Resource warnings | Comparison CSV |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for job, (path, rows, _warning_path, warning_rows) in per_job.items():
        counts = Counter(row["audit_class"] for row in rows)
        matched_total = counts["matched"] + counts["generated_matched"]
        p1 = sum(1 for row in rows if priority_for(row["audit_class"]) == "P1")
        p2 = sum(1 for row in rows if priority_for(row["audit_class"]) == "P2")
        lines.append(
            f"| {job} | {len(rows)} | {matched_total} | {p1} | {p2} | "
            f"{counts['expected_zero_or_utility']} | {len(warning_rows)} | `{format_link(path)}` |"
        )

    lines.extend([
        "",
        "## Audit Classes",
        "",
        "- `Matched`: present with no immediate structural issue in this comparison view.",
        "- `Generated matched`: generated simulator damage and external damage agree in event count without a direct axis press.",
        "- `Expected zero / utility`: buff, step, stance, movement, tincture, or other non-damage action.",
        "- `Generated count delta`: generated damage exists in both simulator and xivintheshell, but event counts differ.",
        "- `Pressed-skill count delta`: pressed skill exists in both, but external damage events differ from axis/sim counts.",
        "- `External generated damage gap`: xivintheshell emits a damage row that the simulator does not model as a separate skill.",
        "- `Auto-attack timing/model gap`: external auto-attack damage exists, but the simulator does not emit matching auto-attack rows.",
        "- `Local damage without external key`: simulator assigns damage to the pressed skill, but xivintheshell assigns no damage key there.",
        "- `Simulator-only generated row`: simulator uses a generic generated-damage bucket such as `Dot Tick`.",
        "",
        "## Per-Job Findings",
        "",
    ])

    for job, (_path, rows, warning_path, warning_rows) in per_job.items():
        lines.extend([
            f"### {job}",
            "",
            JOB_INTERPRETATION[job],
            "",
            *row_table(rows, include_expected=False),
            "",
            "Expected utility rows:",
            "",
        ])
        utility_names = [
            row.get("display_name", "")
            for row in rows
            if row["audit_class"] == "expected_zero_or_utility"
        ]
        if utility_names:
            lines.append(", ".join(utility_names))
        else:
            lines.append("None.")
        lines.extend([
            "",
            f"Resource warnings (`{warning_link(warning_path)}`):",
            "",
            *warning_lines(warning_rows),
            "",
        ])

    lines.extend([
        "## Remaining Evidence Boundary",
        "",
        "1. Treat SMN's manually extended long axis as mechanically loose until it is replaced or supported by real-log / AMAS evidence; the warning CSV identifies the questionable rows.",
        "2. Keep MCH Heat Blast as a known xivintheshell export gap unless a future xivintheshell export emits positive-potency Heat Blast rows.",
        "3. Treat auto-attack count drift as a timing-model boundary for later real-log validation, not as a blocker for Task I skill-level attribution.",
        "4. Smaller count deltas for MNK / DNC / BRD / DRG are now documented review rows; they should be revisited when a stronger external xivintheshell is available.",
        "",
    ])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(str(out_path.relative_to(REPO_ROOT)))


if __name__ == "__main__":
    main()
