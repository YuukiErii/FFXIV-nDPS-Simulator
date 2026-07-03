from functools import lru_cache
from decimal import Decimal


XIVINTHESHELL_APPLICATION_DELAY_OVERRIDES = {
    # Source: xivintheshell/xivintheshell main@81a7c2c, src/Game/Jobs/*.ts.
    # These values mirror applicationDelay for damaging skills where the local
    # AMAS provider currently diverges by more than a frame-scale tolerance.
    ("MNK", "Six-sided Star"): 0.62,
    ("MNK", "The Forbidden Chakra"): 1.48,
    ("DRG", "Wheeling Thrust"): 0.67,
    ("DRG", "Drakesbane"): 1.0,
    ("NIN", "Huton"): 0.98,
    ("NIN", "Doton"): 0.0,
    ("NIN", "Doton (Chi)"): 0.0,
    ("NIN", "Dream Within a Dream"): 0.98,
    ("NIN", "Phantom Kamaitachi"): 1.57,
    ("NIN", "Tenri Jindo"): 0.35,
    ("SAM", "Tendo Goken"): 0.36,
    ("SAM", "Tendo Kaeshi Goken"): 0.36,
    ("RPR", "Shadow of Death"): 1.15,
    ("RPR", "Soul Slice"): 0.99,
    ("RPR", "Gibbet"): 0.5,
    ("RPR", "Gallows"): 0.53,
    ("RPR", "Executioner's Gallows"): 0.62,
    ("RPR", "Communio"): 1.16,
    ("RPR", "Harpe"): 0.9,
    ("RPR", "Harvest Moon"): 0.9,
    ("RPR", "Gluttony"): 1.06,
    ("RPR", "Lemure's Slice"): 0.7,
    ("RPR", "Void Reaping"): 0.53,
    ("RPR", "Cross Reaping"): 0.53,
    ("RPR", "Whorl of Death"): 1.15,
    ("RPR", "Soul Scythe"): 0.66,
    ("RPR", "Executioner's Guillotine"): 0.53,
    ("RPR", "Lemure's Scythe"): 0.66,
    ("VPR", "Writhing Snap"): 0.488,
    ("VPR", "Steel Fangs"): 1.158,
    ("VPR", "Reaving Fangs"): 1.293,
    ("VPR", "Hunter's Sting"): 0.89,
    ("VPR", "Swiftskin's Sting"): 1.16,
    ("VPR", "Flanksting Strike"): 1.649,
    ("VPR", "Flanksbane Fang"): 1.604,
    ("VPR", "Hindsting Strike"): 0.98,
    ("VPR", "Hindsbane Fang"): 1.203,
    ("VPR", "Hunter's Coil"): 0.982,
    ("VPR", "Swiftskin's Coil"): 1.473,
    ("VPR", "Reawaken"): 0.625,
    ("VPR", "Ouroboros"): 2.313,
    ("VPR", "Vicewinder"): 0.581,
    ("VPR", "Uncoiled Fury"): 0.804,
    ("VPR", "Steel Maw"): 1.091,
    ("VPR", "Reaving Maw"): 0.908,
    ("VPR", "Hunter's Bite"): 1.134,
    ("VPR", "Swiftskin's Bite"): 1.445,
    ("VPR", "Jagged Maw"): 1.127,
    ("VPR", "Bloodied Maw"): 0.866,
    ("VPR", "Hunter's Den"): 0.569,
    ("VPR", "Swiftskin's Den"): 0.999,
    ("VPR", "Vicepit"): 0.827,
    ("VPR", "Death Rattle"): 1.697,
    ("VPR", "Last Lash"): 1.226,
    ("VPR", "Twinblood Bite"): 0.714,
    ("VPR", "Twinblood Thresh"): 0.764,
    ("VPR", "Uncoiled Twinfang"): 1.04,
    ("VPR", "Third Legacy"): 1.19,
    ("BRD", "Bloodletter"): 1.65,
    ("MCH", "Gauss Round"): 0.71,
    ("MCH", "Ricochet"): 0.71,
    ("MCH", "Flamethrower"): 0.89,
    ("MCH", "Full Metal Field"): 1.02,
    ("DNC", "Dance of the Dawn"): 0.44,
    ("DNC", "Last Dance"): 1.26,
    ("DNC", "Fan Dance IV"): 0.62,
    ("DNC", "Standard Finish"): 0.54,
    ("DNC", "Single Standard Finish"): 0.54,
    ("DNC", "Double Standard Finish"): 0.54,
    ("DNC", "Technical Finish"): 0.54,
    ("DNC", "Single Technical Finish"): 0.54,
    ("DNC", "Double Technical Finish"): 0.54,
    ("DNC", "Triple Technical Finish"): 0.54,
    ("DNC", "Quadruple Technical Finish"): 0.54,
    ("DNC", "Fan Dance II"): 0.54,
    ("BLM", "Blizzard"): 0.846,
    ("BLM", "Fire"): 1.871,
    ("BLM", "Fire III"): 1.292,
    ("BLM", "Blizzard III"): 0.89,
    ("BLM", "Fire IV"): 1.159,
    ("BLM", "Blizzard IV"): 1.156,
    ("BLM", "Despair"): 0.556,
    ("BLM", "Foul"): 1.158,
    ("BLM", "Freeze"): 0.664,
    ("BLM", "Flare"): 1.157,
    ("BLM", "Paradox"): 0.624,
    ("BLM", "High Thunder"): 0.757,
    ("BLM", "Flare Star"): 0.622,
    ("BLM", "High Thunder II"): 0.8,
    ("SMN", "Tri-disaster"): 0.8,
    ("SMN", "Ruby Catastrophe"): 0.53,
    ("SMN", "Topaz Catastrophe"): 0.53,
    ("SMN", "Emerald Catastrophe"): 0.53,
    ("SMN", "Slipstream"): 1.02,
    ("SMN", "Topaz Rite"): 0.62,
    ("RDM", "Jolt II"): 0.8,
    ("RDM", "Riposte"): 0.62,
    ("RDM", "Zwerchhau"): 0.62,
    ("RDM", "Redoublement"): 0.62,
    ("RDM", "Enchanted Riposte"): 0.62,
    ("RDM", "Enchanted Zwerchhau"): 0.62,
    ("RDM", "Enchanted Redoublement"): 0.62,
    ("RDM", "Reprise"): 0.62,
    ("RDM", "Enchanted Reprise"): 0.62,
    ("RDM", "Corps-a-corps"): 0.62,
    ("RDM", "Engagement"): 0.62,
    ("RDM", "Displacement"): 0.62,
    ("PCT", "Water II in Blue"): 0.89,
    ("PCT", "Thunder in Magenta"): 0.8,
    ("PCT", "Thunder II in Magenta"): 0.8,
}


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
        "name": name,
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
    def __init__(self, version="7.5", level=100):
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
        timing = _select_spec(skill.timing_spec)
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
            "delay": direct_follow_delay if direct_follow_delay is not None else (
                getattr(timing, "application_delay", 500) / 1000.0 if timing else 0.5
            ),
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
        if job == "RPR" and Decimal(str(self.version)) >= Decimal("7.5"):
            potency = {
                "Gluttony": 560,
                "Void Reaping": 580,
                "Cross Reaping": 580,
                "Sacrificium": 700,
            }.get(name)
            if potency is not None:
                out["potency"] = out["base_potency"] = potency
        if job == "DRG" and Decimal(str(self.version)) >= Decimal("7.5") and name == "Starcross":
            out["potency"] = out["base_potency"] = 1000
        if job == "VPR" and Decimal(str(self.version)) >= Decimal("7.5"):
            potency = {
                "Vicewinder": 540,
                "Hunter's Coil": 680,
                "Swiftskin's Coil": 680,
            }.get(name)
            if potency is not None:
                out["potency"] = out["base_potency"] = potency
            if name in {
                "Reawaken", "First Generation", "Second Generation", "Third Generation",
                "Fourth Generation", "Ouroboros", "First Legacy", "Second Legacy",
                "Third Legacy", "Fourth Legacy",
            }:
                out["decay"] = 0.75
        if job == "SMN" and Decimal(str(self.version)) >= Decimal("7.5"):
            potency = {
                "Painflare": 220,
                "Ruby Rite": 620,
                "Crimson Cyclone": 560,
                "Crimson Strike": 560,
                "Necrotize": 500,
            }.get(name)
            if potency is not None:
                out["potency"] = out["base_potency"] = potency
            if name in {"Summon Bahamut", "Summon Phoenix", "Summon Solar Bahamut"}:
                out["delay"] = 0.76
            pet_potency = {
                "Wyrmwave": 120,
                "Scarlet Flame": 120,
                "Luxwave": 128,
                "Akh Morn": 1040,
                "Revelation": 1040,
                "Exodus": 1200,
            }.get(name)
            if pet_potency is not None:
                out["potency"] = out["base_potency"] = pet_potency
                out["job_mod_override"] = None
        if job == "PCT" and name in {"Blizzard in Cyan", "Blizzard II in Cyan"}:
            out["is_aoe"] = name.endswith("II in Cyan")
            out["decay"] = 0.0
        if job == "PCT" and Decimal(str(self.version)) >= Decimal("7.5") and name == "Comet in Black":
            out["decay"] = 0.6
        if job == "BLM" and name in {"Thunder III", "Thunder IV", "High Thunder", "High Thunder II"}:
            out["cast"] = 0.0
        if job == "BLM" and name == "Scathe":
            # ponytail: expected potency for the official 20% chance to double potency.
            out["potency"] = out["base_potency"] = 120
        if job == "MNK" and name == "Enlightenment":
            out["is_gcd"] = False
        delay_override = XIVINTHESHELL_APPLICATION_DELAY_OVERRIDES.get((job, name))
        if delay_override is not None:
            out["delay"] = delay_override
            out["delay_source"] = "xivintheshell"
        return out


@lru_cache(maxsize=4)
def get_amas_provider(version="7.5", level=100):
    try:
        return AmasSkillProvider(version=version, level=level)
    except Exception:
        return None
