try:
    from .base import JobState
except ImportError:
    from base import JobState


class SmnJobState(JobState):
    # xivintheshell's effective SMN pet coefficient. AMAS reaches the same result
    # through pet_scalar=0.88, job mod 100, and excluding the party main-stat bonus.
    PET_DAMAGE_SCALAR = 0.8
    DEMI_AUTO_DELAY = 3.163
    DEMI_APPLICATION_DELAY = 0.76
    PET_APPLICATION_DELAYS = {
        "Summon Ifrit II": 1.96,
        "Summon Ifrit": 0.936,
        "Summon Titan II": 1.96,
        "Summon Titan": 0.8,
        "Summon Garuda II": 1.29,
        "Summon Garuda": 0.8,
        "Enkindle Bahamut": 0.894,
        "Enkindle Phoenix": 1.026,
        "Enkindle Solar Bahamut": 0.846,
    }
    PET_DAMAGE = {
        "Summon Ifrit II": ("Inferno", 800, True),
        "Summon Ifrit": ("Inferno", 600, True),
        "Summon Titan II": ("Earthen Fury", 800, True),
        "Summon Titan": ("Earthen Fury", 600, True),
        "Summon Garuda II": ("Aerial Blast", 800, True),
        "Summon Garuda": ("Aerial Blast", 600, True),
        "Enkindle Bahamut": ("Akh Morn", 1300, True),
        "Enkindle Phoenix": ("Revelation", 1300, True),
        "Enkindle Solar Bahamut": ("Exodus", 1500, True),
    }
    DIRECT_PET_DAMAGE = {
        "Inferno": 800, "Earthen Fury": 800, "Aerial Blast": 800,
        "Akh Morn": 1300, "Revelation": 1300, "Exodus": 1500,
        "Wyrmwave": 150, "Scarlet Flame": 150, "Luxwave": 160,
    }
    DEMI_AUTO = {
        "Summon Bahamut": ("Wyrmwave", 150),
        "Summon Phoenix": ("Scarlet Flame", 150),
        "Summon Solar Bahamut": ("Luxwave", 160),
    }
    PET_SOURCE_SKILLS = set(PET_DAMAGE) | set(DEMI_AUTO)
    DEMI_KINDS = {
        "Summon Bahamut": "bahamut",
        "Summon Phoenix": "phoenix",
        "Summon Solar Bahamut": "solar",
    }
    DEMI_CYCLE = ("solar", "bahamut", "solar", "phoenix")
    DEMI_ACTIONS = {
        "Astral Impulse": "bahamut", "Astral Flare": "bahamut",
        "Deathflare": "bahamut", "Enkindle Bahamut": "bahamut", "Akh Morn": "bahamut",
        "Fountain of Fire": "phoenix", "Brand of Purgatory": "phoenix",
        "Rekindle": "phoenix", "Enkindle Phoenix": "phoenix", "Revelation": "phoenix",
        "Umbral Impulse": "solar", "Umbral Flare": "solar", "Sunflare": "solar",
        "Enkindle Solar Bahamut": "solar", "Exodus": "solar",
    }
    ELEMENT_SUMMONS = {
        "Summon Ifrit II": ("ifrit", 2), "Summon Ifrit": ("ifrit", 2),
        "Summon Titan II": ("titan", 4), "Summon Titan": ("titan", 4),
        "Summon Garuda II": ("garuda", 4), "Summon Garuda": ("garuda", 4),
    }
    ATTUNEMENT_ACTIONS = {
        "Ruby Rite": "ifrit", "Ruby Catastrophe": "ifrit",
        "Topaz Rite": "titan", "Topaz Catastrophe": "titan",
        "Emerald Rite": "garuda", "Emerald Catastrophe": "garuda",
    }

    def __init__(self):
        super().__init__("SMN")
        self.searing_until = -1.0
        self.searing_flash_until = -1.0
        self.further_ruin_until = -1.0
        self.refulgent_lux_until = -1.0
        self.swiftcast_until = -1.0
        self.demi = None
        self.demi_until = -1.0
        self.next_demi_index = 0
        self.arcanum = {"ifrit": False, "titan": False, "garuda": False}
        self.gem = None
        self.gem_until = -1.0
        self.gem_charges = 0
        self.ifrit_favor = False
        self.crimson_strike_ready = False
        self.titan_favor = False
        self.garuda_favor = False
        self.aetherflow = 0
        self._pending_canonical = None

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    @staticmethod
    def _active(until, current_time):
        return until > current_time

    def _active_demi(self, current_time):
        return self.demi if self._active(self.demi_until, current_time) else None

    def _expire(self, current_time):
        if not self._active(self.gem_until, current_time):
            self.gem = None
            self.gem_charges = 0

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Searing Light", "Swiftcast"}

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._pending_canonical = canonical
        self._expire(snapshot_time)
        active_demi = self._active_demi(snapshot_time)
        if canonical != "Swiftcast" and skill.get("cast", 0) and self._active(self.swiftcast_until, current_time):
            self.swiftcast_until = -1.0

        if canonical in self.DEMI_KINDS:
            actual = self.DEMI_KINDS[canonical]
            expected = self.DEMI_CYCLE[self.next_demi_index]
            if active_demi:
                self.warn("smn_demi_overwrite", current_time, name,
                          f"{canonical} used while {active_demi} is still active.")
            if actual != expected:
                self.warn("smn_demi_cycle_mismatch", current_time, name,
                          f"{canonical} used while the tracked next demi is {expected}.")
        elif canonical in self.ELEMENT_SUMMONS:
            gem, _ = self.ELEMENT_SUMMONS[canonical]
            if active_demi:
                self.warn("smn_gem_during_demi", current_time, name,
                          f"{canonical} used while {active_demi} is still active.")
            if not self.arcanum[gem]:
                self.warn("smn_arcanum_missing", current_time, name,
                          f"{canonical} used without tracked {gem} arcanum.")
            if self.gem_charges > 0:
                self.warn("smn_gem_overwrite", current_time, name,
                          f"{canonical} used before spending current {self.gem} attunement.")
        elif canonical in self.ATTUNEMENT_ACTIONS:
            expected = self.ATTUNEMENT_ACTIONS[canonical]
            if self.gem != expected or self.gem_charges <= 0:
                self.warn("smn_gem_action_mismatch", current_time, name,
                          f"{canonical} used without an active {expected} attunement.")

        required_demi = self.DEMI_ACTIONS.get(canonical)
        if required_demi and active_demi != required_demi:
            self.warn("smn_demi_action_mismatch", current_time, name,
                      f"{canonical} requires {required_demi}; tracked demi is {active_demi or 'none'}.")
        if canonical == "Crimson Cyclone" and not self.ifrit_favor:
            self.warn("smn_ifrit_favor_missing", current_time, name,
                      "Crimson Cyclone used without Ifrit's Favor.")
        elif canonical == "Crimson Strike" and not self.crimson_strike_ready:
            self.warn("smn_crimson_strike_not_ready", current_time, name,
                      "Crimson Strike used without Crimson Strike Ready.")
        elif canonical == "Mountain Buster" and not self.titan_favor:
            self.warn("smn_titan_favor_missing", current_time, name,
                      "Mountain Buster used without Titan's Favor.")
        elif canonical == "Slipstream" and not self.garuda_favor:
            self.warn("smn_garuda_favor_missing", current_time, name,
                      "Slipstream used without Garuda's Favor.")
        elif canonical in {"Fester", "Necrotize", "Painflare"} and self.aetherflow <= 0:
            self.warn("smn_aetherflow_empty", current_time, name,
                      f"{canonical} used with no Aetherflow stack.")
        elif canonical == "Ruin IV" and not self._active(self.further_ruin_until, snapshot_time):
            self.warn("smn_further_ruin_missing", current_time, name,
                      "Ruin IV used without Further Ruin.")
        elif canonical == "Searing Flash" and not self._active(self.searing_flash_until, snapshot_time):
            self.warn("smn_searing_flash_not_ready", current_time, name,
                      "Searing Flash used without Ruby's Glimmer.")
        elif canonical == "Lux Solaris" and not self._active(self.refulgent_lux_until, snapshot_time):
            self.warn("smn_refulgent_lux_missing", current_time, name,
                      "Lux Solaris used without Refulgent Lux.")
        return {}

    def on_press_complete(self, name, current_time):
        canonical = self._pending_canonical or name
        self._pending_canonical = None
        self._apply_resource_state(canonical, current_time)

    def _clear_elemental_state(self):
        self.gem = None
        self.gem_until = -1.0
        self.gem_charges = 0
        self.ifrit_favor = False
        self.crimson_strike_ready = False
        self.titan_favor = False
        self.garuda_favor = False

    def _apply_resource_state(self, canonical, current_time):
        if canonical == "Searing Light":
            self.searing_until = current_time + 20.0
            self.searing_flash_until = current_time + 30.0
        elif canonical == "Swiftcast":
            self.swiftcast_until = current_time + 10.0
        elif canonical in self.DEMI_KINDS:
            self.demi = self.DEMI_KINDS[canonical]
            self.demi_until = current_time + 15.0
            self.next_demi_index = (self.next_demi_index + 1) % len(self.DEMI_CYCLE)
            self.arcanum = {"ifrit": True, "titan": True, "garuda": True}
            self._clear_elemental_state()
            if self.demi == "solar":
                self.refulgent_lux_until = current_time + 30.0
        elif canonical in self.ELEMENT_SUMMONS:
            gem, charges = self.ELEMENT_SUMMONS[canonical]
            self.arcanum[gem] = False
            self._clear_elemental_state()
            self.gem = gem
            self.gem_until = current_time + 30.0
            self.gem_charges = charges
            self.ifrit_favor = gem == "ifrit"
            self.garuda_favor = gem == "garuda"
        elif canonical in self.ATTUNEMENT_ACTIONS:
            gem = self.ATTUNEMENT_ACTIONS[canonical]
            if self.gem == gem:
                self.gem_charges = max(0, self.gem_charges - 1)
            if gem == "titan":
                self.titan_favor = True
        elif canonical == "Crimson Cyclone":
            self.ifrit_favor = False
            self.crimson_strike_ready = True
        elif canonical == "Crimson Strike":
            self.crimson_strike_ready = False
        elif canonical == "Mountain Buster":
            self.titan_favor = False
        elif canonical == "Slipstream":
            self.garuda_favor = False
        elif canonical in {"Energy Drain", "Energy Siphon"}:
            self.aetherflow = 2
            self.further_ruin_until = current_time + 60.0
        elif canonical in {"Fester", "Necrotize", "Painflare"}:
            self.aetherflow = max(0, self.aetherflow - 1)
        elif canonical == "Ruin IV":
            self.further_ruin_until = -1.0
        elif canonical == "Searing Flash":
            self.searing_flash_until = -1.0
        elif canonical == "Lux Solaris":
            self.refulgent_lux_until = -1.0

    def effective_cast_time(self, name, skill, event, current_time, default_cast_time):
        if event and event.get("cast_time") is not None:
            return default_cast_time
        if default_cast_time > 0 and self._active(self.swiftcast_until, current_time):
            return 0.0
        return default_cast_time

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical in self.DIRECT_PET_DAMAGE:
            return int(round(self.DIRECT_PET_DAMAGE[canonical] * self.PET_DAMAGE_SCALAR)), False
        if canonical in self.PET_SOURCE_SKILLS:
            return 0, False
        return super().resolve_potency(name, skill, current_time, payload)

    def _followup(self, name, tooltip_potency, delay, targets=1, is_aoe=False, searing_snapshot=None):
        event = {
            "name": name,
            "potency": int(round(tooltip_potency * self.PET_DAMAGE_SCALAR)),
            "delay": delay,
            "targets": targets,
            "is_aoe": is_aoe,
            "decay": 0.5 if is_aoe else 0.0,
            "damage_class": "PET",
        }
        if searing_snapshot is not None:
            event["smn_searing_snapshot"] = bool(searing_snapshot)
            event["snapshot_potion_now"] = True
        else:
            event["snapshot_potion_at_followup"] = True
        return event

    def followup_damage_events(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        target_count = int(payload.get("targets", 1))
        if canonical in self.PET_DAMAGE:
            pet_name, potency, is_aoe = self.PET_DAMAGE[canonical]
            delay = self.PET_APPLICATION_DELAYS.get(canonical, 0.0)
            return [self._followup(
                pet_name,
                potency,
                delay,
                target_count if is_aoe else 1,
                is_aoe,
                self._active(self.searing_until, current_time),
            )]

        if canonical in self.DEMI_AUTO:
            auto_name, potency = self.DEMI_AUTO[canonical]
            first_delay = max(0.0, self.DEMI_AUTO_DELAY - self.DEMI_APPLICATION_DELAY)
            return [
                self._followup(auto_name, potency, first_delay + self.DEMI_AUTO_DELAY * i)
                for i in range(4)
            ]
        return []

    def active_damage_buffs(self, t, target_id=None):
        self._expire(t)
        searing = self._active(self.searing_until, t)
        return {
            "smn_searing": searing,
            "smn_demi": self._active_demi(t),
            "smn_gem": self.gem if self.gem_charges > 0 else None,
            "damage_mult": 1.05 if searing else 1.0,
        }

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("smn_searing"):
            labels.append("灼热")
        if active_buffs.get("smn_demi"):
            labels.append("龙神")
        if active_buffs.get("smn_gem"):
            labels.append("宝石")
        if has_potion:
            labels.append("药")
        return labels
