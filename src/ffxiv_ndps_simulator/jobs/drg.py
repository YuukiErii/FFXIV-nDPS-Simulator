try:
    from .base import JobState
except ImportError:
    from base import JobState


class DrgJobState(JobState):
    MELEE_WEAPONSKILLS = {
        "True Thrust", "Raiden Thrust", "Lance Barrage", "Heavens' Thrust",
        "Spiral Blow", "Chaotic Spring", "Fang and Claw", "Wheeling Thrust",
        "Drakesbane", "Doom Spike", "Draconian Fury", "Sonic Thrust",
        "Coerthan Torment", "Vorpal Thrust", "Full Thrust", "Chaos Thrust",
    }
    DRACONIAN_FIRE_GENERATORS = {"Drakesbane", "Coerthan Torment"}
    DRACONIAN_FIRE_SPENDERS = {"Raiden Thrust", "Draconian Fury"}

    def __init__(self):
        super().__init__("DRG")
        self.life_surge_until = -1.0
        self.life_surge_ready = False
        self.lance_charge_until = -1.0
        self.battle_litany_start = -1.0
        self.battle_litany_until = -1.0
        self.life_of_the_dragon_until = -1.0
        self.nastrond_ready_until = -1.0
        self.starcross_ready_until = -1.0
        self.dragons_flight_until = -1.0
        self.dive_ready_until = -1.0
        self.draconian_fire_until = -1.0
        self.firstminds_focus = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    @staticmethod
    def _active(until, current_time):
        return JobState._active_until(until, current_time)

    def _can_life_surge(self, canonical, skill):
        return bool(skill.get("potency", 0) > 0 and (skill.get("is_gcd") or canonical in self.MELEE_WEAPONSKILLS))

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Life Surge", "Lance Charge", "Battle Litany"}

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        out = {}
        if canonical == "Nastrond" and not self._active(self.nastrond_ready_until, snapshot_time):
            self.warn("drg_nastrond_not_ready", current_time, name,
                      "Nastrond used without tracked Nastrond Ready.")
        if canonical == "Stardiver" and not self._active(self.life_of_the_dragon_until, snapshot_time):
            self.warn("drg_life_inactive", current_time, name,
                      "Stardiver used outside a tracked Life of the Dragon window.")
        if canonical == "Starcross" and not self._active(self.starcross_ready_until, snapshot_time):
            self.warn("drg_starcross_not_ready", current_time, name,
                      "Starcross used without tracked Starcross Ready.")
        if canonical == "Rise of the Dragon" and not self._active(self.dragons_flight_until, snapshot_time):
            self.warn("drg_dragons_flight_not_ready", current_time, name,
                      "Rise of the Dragon used without tracked Dragon's Flight.")
        if canonical == "Mirage Dive" and not self._active(self.dive_ready_until, snapshot_time):
            self.warn("drg_dive_ready_missing", current_time, name,
                      "Mirage Dive used without tracked Dive Ready.")
        if canonical in self.DRACONIAN_FIRE_SPENDERS and not self._active(self.draconian_fire_until, snapshot_time):
            self.warn("drg_draconian_fire_missing", current_time, name,
                      f"{canonical} used without tracked Draconian Fire.")
        if canonical == "Wyrmwind Thrust" and self.firstminds_focus < 2:
            self.warn("drg_firstminds_low", current_time, name,
                      f"Wyrmwind Thrust used with Firstminds' Focus {self.firstminds_focus}; expected 2.")
        if self.life_surge_ready and self._active(self.life_surge_until, snapshot_time) and self._can_life_surge(canonical, skill):
            out["guaranteed_crit"] = True
            self.life_surge_ready = False
            self.life_surge_until = -1.0
        return out

    def on_press_complete(self, name, current_time):
        return None

    def on_press_confirmed(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Life Surge":
            self.life_surge_ready = True
            self.life_surge_until = current_time + 5.0
        elif canonical == "Lance Charge":
            self.lance_charge_until = current_time + 20.0
        elif canonical == "Battle Litany":
            self.battle_litany_start, self.battle_litany_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
        elif canonical == "Dragonfire Dive":
            self.dragons_flight_until = current_time + 30.0
        return None

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if payload.get("press_time") is not None and canonical in {"Life Surge", "Lance Charge", "Battle Litany"}:
            return
        if canonical == "Life Surge":
            self.life_surge_ready = True
            self.life_surge_until = current_time + 5.0
        elif canonical == "Lance Charge":
            self.lance_charge_until = current_time + 20.0
        elif canonical == "Battle Litany":
            self.battle_litany_start, self.battle_litany_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
        elif canonical == "Geirskogul":
            self.life_of_the_dragon_until = current_time + 20.0
            self.nastrond_ready_until = current_time + 20.0
            self.starcross_ready_until = min(self.starcross_ready_until, self.life_of_the_dragon_until)
        elif canonical in {"Jump", "High Jump"}:
            self.dive_ready_until = current_time + 15.0
        elif canonical == "Mirage Dive":
            self.dive_ready_until = -1.0
        elif canonical == "Rise of the Dragon":
            self.dragons_flight_until = -1.0
        elif canonical == "Stardiver":
            if self._active(self.life_of_the_dragon_until, current_time):
                self.starcross_ready_until = min(current_time + 20.0, self.life_of_the_dragon_until)
        elif canonical == "Starcross":
            self.starcross_ready_until = -1.0
        landed = payload.get("source_roll_available", True)
        if canonical in self.MELEE_WEAPONSKILLS and self._active(self.draconian_fire_until, current_time):
            if landed and canonical in self.DRACONIAN_FIRE_SPENDERS:
                self.firstminds_focus = min(2, self.firstminds_focus + 1)
            self.draconian_fire_until = -1.0
        if landed and is_combo and canonical in self.DRACONIAN_FIRE_GENERATORS:
            self.draconian_fire_until = current_time + 30.0
        elif canonical == "Wyrmwind Thrust":
            self.firstminds_focus = 0

    def active_damage_buffs(self, t, target_id=None):
        lance_charge = self._active(self.lance_charge_until, t)
        battle_litany = self._active_window(self.battle_litany_start, self.battle_litany_until, t)
        damage_mult = 1.0
        damage_factors = []
        if lance_charge:
            damage_mult *= 1.10
            damage_factors.append(("猛枪", 1.10))
        active = {
            "drg_lance_charge": lance_charge,
            "drg_battle_litany": battle_litany,
            "drg_life": self._active(self.life_of_the_dragon_until, t),
            "damage_mult": damage_mult,
            "damage_factors": damage_factors,
            "crit_rate_add": 0.10 if battle_litany else 0.0,
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
