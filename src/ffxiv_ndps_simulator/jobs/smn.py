try:
    from .base import JobState
except ImportError:
    from base import JobState


class SmnJobState(JobState):
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
        "Summon Ifrit II": ("Inferno", 640),
        "Summon Ifrit": ("Inferno", 600),
        "Summon Titan II": ("Earthen Fury", 640),
        "Summon Titan": ("Earthen Fury", 600),
        "Summon Garuda II": ("Aerial Blast", 640),
        "Summon Garuda": ("Aerial Blast", 600),
        "Enkindle Bahamut": ("Akh Morn", 1040),
        "Enkindle Phoenix": ("Revelation", 1040),
        "Enkindle Solar Bahamut": ("Exodus", 1200),
    }
    DEMI_AUTO = {
        "Summon Bahamut": ("Wyrmwave", 120),
        "Summon Phoenix": ("Scarlet Flame", 120),
        "Summon Solar Bahamut": ("Luxwave", 128),
    }
    PET_SOURCE_SKILLS = set(PET_DAMAGE) | set(DEMI_AUTO) | {"Akh Morn"}
    GEM_ACTIONS = {
        "Ruby Rite": "ifrit",
        "Ruby Catastrophe": "ifrit",
        "Crimson Cyclone": "ifrit",
        "Crimson Strike": "ifrit",
        "Topaz Rite": "titan",
        "Topaz Catastrophe": "titan",
        "Mountain Buster": "titan",
        "Emerald Rite": "garuda",
        "Emerald Catastrophe": "garuda",
        "Slipstream": "garuda",
    }
    DEMI_ACTIONS = {"Deathflare", "Akh Morn", "Sunflare", "Lux Solaris"}

    def __init__(self):
        super().__init__("SMN")
        self.searing_until = -1.0
        self.demi = None
        self.demi_until = -1.0
        self.gem = None
        self.gem_until = -1.0
        self.gem_charges = 0
        self.aetherflow = 0
        self._pending_canonical = None

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) == "Searing Light"

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._pending_canonical = canonical
        if canonical in {"Summon Ifrit II", "Summon Ifrit", "Summon Titan II", "Summon Titan",
                         "Summon Garuda II", "Summon Garuda"}:
            if self.demi_until > snapshot_time:
                self.warn("smn_gem_during_demi", current_time, name,
                          f"{canonical} used while {self.demi} is still active.")
            if self.gem_charges > 0 and self.gem_until > snapshot_time:
                self.warn("smn_gem_overwrite", current_time, name,
                          f"{canonical} used before spending current {self.gem} gem charges.")
        elif canonical in self.GEM_ACTIONS:
            expected = self.GEM_ACTIONS[canonical]
            if self.gem != expected or self.gem_until <= snapshot_time or self.gem_charges <= 0:
                self.warn("smn_gem_action_mismatch", current_time, name,
                          f"{canonical} used without an active {expected} gem charge.")
        elif canonical in self.DEMI_ACTIONS and self.demi_until <= snapshot_time:
            self.warn("smn_demi_action_inactive", current_time, name,
                      f"{canonical} used without an active demi summon.")
        elif canonical in {"Fester", "Necrotize", "Painflare"} and self.aetherflow <= 0:
            self.warn("smn_aetherflow_empty", current_time, name,
                      f"{canonical} used with no Aetherflow stack.")
        return {}

    def on_press_complete(self, name, current_time):
        canonical = self._pending_canonical or name
        self._pending_canonical = None
        self._apply_resource_state(canonical, current_time)

    def _apply_resource_state(self, canonical, current_time):
        if canonical == "Searing Light":
            self.searing_until = current_time + 20.0
        elif canonical in {"Summon Bahamut", "Summon Phoenix", "Summon Solar Bahamut"}:
            self.demi = canonical
            self.demi_until = current_time + 15.0
        elif canonical in {"Summon Ifrit II", "Summon Ifrit"}:
            self.gem = "ifrit"
            self.gem_until = current_time + 30.0
            self.gem_charges = 2
        elif canonical in {"Summon Titan II", "Summon Titan"}:
            self.gem = "titan"
            self.gem_until = current_time + 30.0
            self.gem_charges = 4
        elif canonical in {"Summon Garuda II", "Summon Garuda"}:
            self.gem = "garuda"
            self.gem_until = current_time + 30.0
            self.gem_charges = 4
        elif canonical in {"Energy Drain", "Energy Siphon"}:
            self.aetherflow = 2
        elif canonical in {"Fester", "Necrotize", "Painflare"}:
            self.aetherflow = max(0, self.aetherflow - 1)
        elif canonical in self.GEM_ACTIONS:
            self.gem_charges = max(0, self.gem_charges - 1)

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical in self.PET_SOURCE_SKILLS:
            return 0, False
        return super().resolve_potency(name, skill, current_time, payload)

    def _followup(self, name, potency, delay, targets=1):
        return {
            "name": name,
            "potency": potency,
            "delay": delay,
            "targets": targets,
            "damage_class": "PET",
        }

    def followup_damage_events(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        target_count = int(payload.get("targets", 1))
        if canonical in self.PET_DAMAGE:
            pet_name, potency = self.PET_DAMAGE[canonical]
            delay = self.PET_APPLICATION_DELAYS.get(canonical, 0.8)
            return [self._followup(pet_name, potency, delay, target_count)]

        if canonical in self.DEMI_AUTO:
            auto_name, potency = self.DEMI_AUTO[canonical]
            first_delay = max(0.0, self.DEMI_AUTO_DELAY - self.DEMI_APPLICATION_DELAY)
            return [
                self._followup(auto_name, potency, first_delay + self.DEMI_AUTO_DELAY * i, target_count)
                for i in range(4)
            ]

        return []

    def active_damage_buffs(self, t, target_id=None):
        return {
            "smn_searing": self.searing_until > t,
            "smn_demi": self.demi if self.demi_until > t else None,
            "smn_gem": self.gem if self.gem_until > t else None,
            "damage_mult": 1.05 if self.searing_until > t else 1.0,
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
