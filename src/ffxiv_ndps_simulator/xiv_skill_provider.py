from functools import lru_cache


def _forced_name(value):
    return getattr(value, "name", str(value))


def _is_gcd_skill(skill):
    explicit = getattr(skill, "is_GCD", None)
    if explicit is not None:
        return bool(explicit)
    return _forced_name(getattr(skill, "skill_type", "")) in {"SPELL", "WEAPONSKILL"}


def _select_spec(specs, prefer_no_combo=False):
    if specs is None:
        return None
    if not isinstance(specs, dict):
        return specs
    if prefer_no_combo:
        for conditions, spec in specs.items():
            if "No Combo" in conditions and "No Positional" not in conditions:
                return spec
    for conditions, spec in specs.items():
        if len(conditions) == 0:
            return spec
    for conditions, spec in specs.items():
        if spec is not None:
            return spec
    return None


def _select_followups(followups):
    if not isinstance(followups, dict):
        return followups or ()
    for conditions, items in followups.items():
        if len(conditions) == 0:
            return items or ()
    return ()


def _select_direct_followup(followups, prefer_no_combo=False):
    selected = ()
    if isinstance(followups, dict):
        if prefer_no_combo:
            for conditions, items in followups.items():
                if "No Combo" in conditions and "No Positional" not in conditions:
                    selected = items or ()
                    break
        if not selected:
            for conditions, items in followups.items():
                if len(conditions) == 0:
                    selected = items or ()
                    break
    else:
        selected = followups or ()
    for follow in selected:
        if getattr(follow, "dot_duration", None):
            continue
        skill = getattr(follow, "skill", None)
        spec = _select_spec(getattr(skill, "damage_spec", None))
        if spec is not None:
            delay = (getattr(follow, "delay_after_parent_application", 0) or 0) / 1000.0
            return spec, delay, skill
    return None, None, None


def _combo_prev(combo_spec):
    specs = combo_spec
    if isinstance(specs, dict):
        specs = specs.get(frozenset(), ())
    if not isinstance(specs, tuple):
        specs = (specs,)
    prev = []
    for spec in specs:
        for action in getattr(spec, "combo_actions", ()) or ():
            if action not in prev:
                prev.append(action)
    return prev


def _buff_spec_to_dict(spec, name):
    if spec is None:
        return None
    if isinstance(spec, dict):
        spec = spec.get(frozenset())
    if spec is None:
        return None
    duration_ms = getattr(spec, "duration", 0) or getattr(spec, "max_duration", 0)
    if duration_ms <= 0:
        return None
    return {
        "key": f"buff:{name}",
        "duration": duration_ms / 1000.0,
        "damage_mult": float(getattr(spec, "damage_mult", 1.0) or 1.0),
        "crit_rate_add": float(getattr(spec, "crit_rate_add", 0.0) or 0.0),
        "dh_rate_add": float(getattr(spec, "dh_rate_add", 0.0) or 0.0),
        "main_stat_add": float(getattr(spec, "main_stat_add", 0.0) or 0.0),
        "main_stat_mult": float(getattr(spec, "main_stat_mult", 1.0) or 1.0),
        "auto_attack_delay_reduction": float(getattr(spec, "auto_attack_delay_reduction", 0.0) or 0.0),
        "haste_time_reduction": float(getattr(spec, "haste_time_reduction", 0.0) or 0.0),
    }


class AmasSkillProvider:
    def __init__(self, version="7.2", level=100):
        from ama_xiv_combat_sim.simulator.skills.create_skill_library import create_skill_library

        self.version = version
        self.level = level
        self.library = create_skill_library(version, level=level)

    def has_job(self, job):
        return self.library.has_job_class(job)

    def has_skill(self, job, name):
        try:
            return self.library.has_skill(name, job)
        except KeyError:
            return False

    def get(self, job, name):
        if not self.has_skill(job, name):
            return None
        skill = self.library.get_skill(name, job)
        timing = skill.timing_spec
        main_spec = _select_spec(skill.damage_spec)
        no_combo_spec = _select_spec(skill.damage_spec, prefer_no_combo=True)
        direct_follow_spec, direct_follow_delay, direct_follow_skill = _select_direct_followup(skill.follow_up_skills)
        direct_no_combo_spec, _, _ = _select_direct_followup(skill.follow_up_skills, prefer_no_combo=True)
        damage_skill = skill
        if main_spec is None and direct_follow_spec is not None:
            main_spec = direct_follow_spec
            damage_skill = direct_follow_skill or skill
        if no_combo_spec is None and direct_no_combo_spec is not None:
            no_combo_spec = direct_no_combo_spec
        potency = getattr(main_spec, "potency", 0) if main_spec is not None else 0
        base_potency = getattr(no_combo_spec, "potency", potency) if no_combo_spec is not None else potency
        aoe_dropoff = getattr(skill, "aoe_dropoff", None)
        if aoe_dropoff is None and damage_skill is not skill:
            aoe_dropoff = getattr(damage_skill, "aoe_dropoff", None)
        is_aoe = bool(getattr(skill, "has_aoe", False) or getattr(damage_skill, "has_aoe", False))
        if job == "NIN" and name in {
            "Katon", "Huton", "Goka Mekkyaku", "Hollow Nozuchi", "Deathfrog Medium",
        }:
            is_aoe = True
        out = {
            "cast": (getattr(timing, "base_cast_time", 0) or 0) / 1000.0 if timing else 0.0,
            "delay": direct_follow_delay if direct_follow_delay is not None else (getattr(timing, "application_delay", 500) or 500) / 1000.0 if timing else 0.5,
            "potency": potency or 0,
            "base_potency": base_potency or potency or 0,
            "combo_prev": _combo_prev(skill.combo_spec),
            "is_gcd": _is_gcd_skill(skill),
            "guaranteed_crit": _forced_name(getattr(main_spec, "guaranteed_crit", "")) == "FORCE_YES",
            "guaranteed_dh": _forced_name(getattr(main_spec, "guaranteed_dh", "")) == "FORCE_YES",
            "is_aoe": is_aoe,
            "decay": float(aoe_dropoff or 0.0),
            "buff": _buff_spec_to_dict(skill.offensive_buff_spec, name),
            "damage_class": getattr(getattr(main_spec, "damage_class", None), "name", ""),
            "job_mod_override": getattr(main_spec, "pet_job_mod_override", None),
        }

        for follow in _select_followups(skill.follow_up_skills):
            dot_duration = getattr(follow, "dot_duration", None)
            dot_skill = getattr(follow, "skill", None)
            dot_spec = getattr(dot_skill, "damage_spec", None)
            dot_spec = _select_spec(dot_spec)
            follow_buff = _buff_spec_to_dict(getattr(dot_skill, "offensive_buff_spec", None), getattr(dot_skill, "name", name))
            if follow_buff:
                out["buff"] = follow_buff
                if getattr(dot_skill, "name", "") == "Fugetsu":
                    out["grants"] = "fugetsu"
                elif getattr(dot_skill, "name", "") == "Fuka":
                    out["grants"] = "shifu"
            if dot_duration and dot_spec is not None:
                out["dot_name"] = getattr(dot_skill, "name", f"{name} (dot)")
                out["dot_potency"] = getattr(dot_spec, "potency", 0) or 0
                out["dot_duration"] = dot_duration / 1000.0
                out["dot_primary_only"] = bool(getattr(follow, "primary_target_only", True))
                break
        return out


@lru_cache(maxsize=4)
def get_amas_provider(version="7.2", level=100):
    try:
        return AmasSkillProvider(version=version, level=level)
    except Exception:
        return None
