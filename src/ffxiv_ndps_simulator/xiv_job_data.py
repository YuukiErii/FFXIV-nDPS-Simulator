import os
import re
import sys
from dataclasses import dataclass


DPS_JOB_ORDER = (
    "MNK", "DRG", "NIN", "SAM", "RPR", "VPR",
    "BRD", "MCH", "DNC",
    "BLM", "SMN", "RDM", "PCT",
)


STAT_SCHEMA_MAIN = {
    "dpsStr": "STR",
    "dpsDex": "DEX",
    "dpsInt": "INT",
}


@dataclass(frozen=True)
class LevelModifiers:
    main: int
    sub: int
    div: int
    det: int
    det_trunc: int
    ap: int
    ap_tank: int


@dataclass(frozen=True)
class JobProfile:
    code: str
    name: str
    main_stat: str
    speed_stat: str
    job_mod: int
    trait_damage_multiplier: float
    gcd_modifier: float
    party_bonus: float
    level_modifiers: LevelModifiers

    @property
    def is_caster(self):
        return self.main_stat in {"INT", "MND"}


def _extract_balanced_object(text, start):
    depth = 0
    in_string = None
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1], idx + 1
    raise ValueError("Unbalanced TypeScript object")


def _parse_number_map(body):
    parsed = {}
    for key, raw in re.findall(r"(\w+):\s*([0-9.]+)", body):
        parsed[key] = float(raw) if "." in raw else int(raw)
    return parsed


def _parse_level_modifiers(game_text, level=100):
    match = re.search(rf"\b{level}:\s*\{{", game_text)
    if not match:
        raise ValueError(f"Could not find level {level} modifiers in game.txt")
    block, _ = _extract_balanced_object(game_text, match.end() - 1)
    vals = _parse_number_map(block)
    return LevelModifiers(
        main=int(vals["main"]),
        sub=int(vals["sub"]),
        div=int(vals["div"]),
        det=int(vals.get("det", vals["div"])),
        det_trunc=int(vals.get("detTrunc", 1)),
        ap=int(vals["ap"]),
        ap_tank=int(vals["apTank"]),
    )


def _parse_stat_modifiers(schema_body):
    match = re.search(r"statModifiers:\s*\{", schema_body)
    if not match:
        return {}
    block, _ = _extract_balanced_object(schema_body, match.end() - 1)
    return _parse_number_map(block)


def _parse_job_profiles(game_text, level=100):
    level_mods = _parse_level_modifiers(game_text, level=level)
    root = re.search(r"export const jobSchemas\s*=\s*\{", game_text)
    if not root:
        raise ValueError("Could not find jobSchemas in game.txt")
    schemas_body, _ = _extract_balanced_object(game_text, root.end() - 1)
    profiles = {}

    pos = 0
    while True:
        match = re.search(r"\n\s*([A-Z]{3}):\s*\{", schemas_body[pos:])
        if not match:
            break
        code = match.group(1)
        start = pos + match.end() - 1
        body, end = _extract_balanced_object(schemas_body, start)
        pos = end

        if code not in DPS_JOB_ORDER:
            continue
        schema_ref = re.search(r"stats:\s*statSchemas\.(\w+)", body)
        schema_name = schema_ref.group(1) if schema_ref else ""
        main_stat = re.search(r"mainStat:\s*'(\w+)'", body)
        main_stat = main_stat.group(1) if main_stat else STAT_SCHEMA_MAIN.get(schema_name, "STR")
        speed_stat = "SPS" if main_stat in {"INT", "MND"} else "SKS"
        name = re.search(r"name:\s*'([^']+)'", body)
        modifiers = _parse_stat_modifiers(body)
        job_mod = int(modifiers.get(main_stat, 100))
        trait = re.search(r"traitDamageMultiplier:\s*([0-9.]+)", body)
        gcd_mod = float(modifiers.get("gcd", 100)) / 100.0
        party_bonus = re.search(r"partyBonus:\s*([0-9.]+)", body)

        profiles[code] = JobProfile(
            code=code,
            name=name.group(1) if name else code,
            main_stat=main_stat,
            speed_stat=speed_stat,
            job_mod=job_mod,
            trait_damage_multiplier=float(trait.group(1)) if trait else 1.0,
            gcd_modifier=gcd_mod,
            party_bonus=float(party_bonus.group(1)) if party_bonus else 1.05,
            level_modifiers=level_mods,
        )
    return profiles


def _profile_base_dir_candidates(base_dir=None):
    if base_dir is not None:
        return [base_dir]
    module_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [module_dir]
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.extend([
            os.path.join(bundle_root, "ffxiv_ndps_simulator"),
            bundle_root,
        ])
    return candidates


def load_job_profiles(base_dir=None, level=100):
    path = None
    for candidate_dir in _profile_base_dir_candidates(base_dir):
        candidate = os.path.join(candidate_dir, "game.txt")
        if os.path.exists(candidate):
            path = candidate
            break
    if path is None:
        path = os.path.join(_profile_base_dir_candidates(base_dir)[0], "game.txt")
    with open(path, "r", encoding="utf-8") as f:
        return _parse_job_profiles(f.read(), level=level)


def get_job_profiles(base_dir=None, level=100):
    try:
        profiles = load_job_profiles(base_dir=base_dir, level=level)
    except Exception:
        level_mods = LevelModifiers(main=440, sub=420, div=2780, det=2780, det_trunc=1, ap=237, ap_tank=190)
        profiles = {
            "SAM": JobProfile(
                code="SAM", name="武士", main_stat="STR", speed_stat="SKS",
                job_mod=112, trait_damage_multiplier=1.0, gcd_modifier=0.87,
                party_bonus=1.05, level_modifiers=level_mods,
            )
        }
    return {k: profiles[k] for k in DPS_JOB_ORDER if k in profiles}


JOB_PROFILES = get_job_profiles()
