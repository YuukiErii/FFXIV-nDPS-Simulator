try:
    from .base import JobState
except ImportError:
    from base import JobState


class DrgJobState(JobState):
    LIFE_SURGE_ALLOWLIST = {
        "True Thrust", "Raiden Thrust", "Spiral Blow", "Chaotic Spring",
        "Vorpal Thrust", "Lance Barrage", "Full Thrust", "Heavens' Thrust",
        "Fang and Claw", "Wheeling Thrust", "Drakesbane",
        "Doom Spike", "Draconian Fury", "Sonic Thrust", "Coerthan Torment",
    }

    def __init__(self):
        super().__init__("DRG")
        self.life_surge_until = -1.0
        self.life_surge_ready = False
        self.lance_charge_until = -1.0
        self.battle_litany_until = -1.0
        self.life_of_the_dragon_until = -1.0
        self.firstminds_focus = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Life Surge", "Lance Charge", "Battle Litany"}

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        out = {}
        if canonical in {"Nastrond", "Stardiver", "Starcross", "Rise of the Dragon"}:
            if self.life_of_the_dragon_until <= snapshot_time:
                self.warn("drg_life_inactive", current_time, name,
                          f"{canonical} used outside a tracked Life of the Dragon window.")
        if canonical == "Wyrmwind Thrust" and self.firstminds_focus < 2:
            self.warn("drg_firstminds_low", current_time, name,
                      f"Wyrmwind Thrust used with Firstminds' Focus {self.firstminds_focus}; expected 2.")
        if self.life_surge_ready and self.life_surge_until > snapshot_time and canonical in self.LIFE_SURGE_ALLOWLIST:
            out["guaranteed_crit"] = True
            self.life_surge_ready = False
            self.life_surge_until = -1.0
        return out

    def on_press_complete(self, name, current_time):
        return None

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Life Surge":
            self.life_surge_ready = True
            self.life_surge_until = current_time + 5.0
        elif canonical == "Lance Charge":
            self.lance_charge_until = current_time + 20.0
        elif canonical == "Battle Litany":
            self.battle_litany_until = current_time + 20.0
        elif canonical == "Geirskogul":
            self.life_of_the_dragon_until = current_time + 20.0
        elif canonical in {"Raiden Thrust", "Draconian Fury", "Drakesbane"}:
            self.firstminds_focus = min(2, self.firstminds_focus + 1)
        elif canonical == "Wyrmwind Thrust":
            self.firstminds_focus = 0

    def active_damage_buffs(self, t, target_id=None):
        active = {
            "drg_lance_charge": self.lance_charge_until > t,
            "drg_battle_litany": self.battle_litany_until > t,
            "drg_life": self.life_of_the_dragon_until > t,
            "damage_mult": 1.10 if self.lance_charge_until > t else 1.0,
            "crit_rate_add": 0.10 if self.battle_litany_until > t else 0.0,
        }
        return active

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("drg_lance_charge"):
            labels.append("猛枪")
        if active_buffs.get("drg_battle_litany"):
            labels.append("连祷")
        if active_buffs.get("drg_life"):
            labels.append("红龙")
        if has_potion:
            labels.append("药")
        return labels
