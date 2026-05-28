try:
    from .base import JobState
except ImportError:
    from base import JobState


class BlmJobState(JobState):
    ENOCHIAN_MULT = 1.27
    ELEMENT_TIMEOUT = 15.0

    FIRE_ASPECT = {
        "Fire", "Fire III", "Fire IV", "High Fire II",
        "Despair", "Flare", "Flare Star",
    }
    ICE_ASPECT = {
        "Blizzard", "Blizzard III", "Blizzard IV", "High Blizzard II", "Freeze",
    }
    THUNDER_SPELLS = {"Thunder III", "Thunder IV", "High Thunder", "High Thunder II"}
    FIRE_MP_COSTS = {
        "Fire": 800,
        "Fire III": 2000,
        "Fire IV": 800,
        "High Fire II": 1500,
        "Despair": 800,
        "Flare": 800,
    }

    def __init__(self):
        super().__init__("BLM")
        self.astral_fire = 0
        self.umbral_ice = 0
        self.umbral_hearts = 0
        self.astral_soul = 0
        self.polyglot = 0
        self.paradox = 0
        self.thunderhead = 0
        self.firestarter = 0
        self.mp = 10000
        self.enochian_until = -1.0
        self.ley_lines_until = -1.0
        self.swiftcast_until = -1.0
        self.triplecast_stacks = 0
        self.triplecast_until = -1.0
        self._pending_canonical = None

    def _canonical(self, name, skill=None):
        if skill:
            return skill.get("amas_name") or skill.get("canonical_name") or name
        return name

    def _refresh_enochian(self, current_time):
        self.enochian_until = current_time + self.ELEMENT_TIMEOUT

    def _has_enochian(self, current_time):
        return self.enochian_until > current_time and (self.astral_fire > 0 or self.umbral_ice > 0)

    def _switch_to_astral_fire(self, stacks, current_time):
        if self.astral_fire <= 0:
            self.thunderhead = 1
            if self.umbral_ice >= 3 and self.umbral_hearts >= 3:
                self.paradox = 1
        self.astral_fire = min(3, max(self.astral_fire, stacks))
        self.umbral_ice = 0
        self._refresh_enochian(current_time)

    def _switch_to_umbral_ice(self, stacks, current_time):
        if self.umbral_ice <= 0:
            self.thunderhead = 1
            if self.astral_fire >= 3:
                self.paradox = 1
        self.umbral_ice = min(3, max(self.umbral_ice, stacks))
        self.astral_fire = 0
        self.astral_soul = 0
        self._refresh_enochian(current_time)

    def _consume_instant_cast_status(self, canonical):
        if canonical in {"Despair", "Foul", "Xenoglossy", "Paradox", "Umbral Soul"}:
            return
        if self.swiftcast_until > -1.0:
            self.swiftcast_until = -1.0
            return
        if self.triplecast_stacks > 0:
            self.triplecast_stacks -= 1

    def handles_skill_buff(self, name, skill):
        return bool(skill.get("buff"))

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._pending_canonical = canonical
        if canonical in {"Fire IV", "Despair", "Flare Star"} and self.astral_fire <= 0:
            self.warn("blm_astral_fire_missing", current_time, name,
                      f"{canonical} used without a tracked Astral Fire state.")
        if canonical in self.THUNDER_SPELLS and self.thunderhead <= 0:
            self.warn("blm_thunderhead_missing", current_time, name,
                      f"{canonical} used without a tracked Thunderhead state.")
        if canonical in {"Foul", "Xenoglossy"} and self.polyglot <= 0:
            self.warn("blm_polyglot_empty", current_time, name,
                      f"{canonical} used with no tracked Polyglot stack.")
        if canonical == "Flare Star" and self.astral_soul < 6:
            self.warn("blm_astral_soul_low", current_time, name,
                      f"Flare Star used with Astral Soul {self.astral_soul}; expected 6.")
        mp_cost = self.FIRE_MP_COSTS.get(canonical, 0)
        if mp_cost and self.umbral_ice <= 0 and self.mp < mp_cost:
            self.warn("blm_mp_low", current_time, name,
                      f"{canonical} used with MP {self.mp}; expected at least {mp_cost}.")
        if skill.get("cast", 0) or canonical in self.FIRE_ASPECT or canonical in self.ICE_ASPECT:
            self._consume_instant_cast_status(canonical)
        return {}

    def on_press_complete(self, name, current_time):
        canonical = self._pending_canonical or name
        self._pending_canonical = None
        self._apply_action(canonical, current_time)

    def _aspect_multiplier(self, canonical):
        if canonical in self.FIRE_ASPECT:
            if self.astral_fire == 1:
                return 1.4
            if self.astral_fire == 2:
                return 1.6
            if self.astral_fire == 3:
                return 1.8
            if self.umbral_ice == 1:
                return 0.9
            if self.umbral_ice == 2:
                return 0.8
            if self.umbral_ice == 3:
                return 0.7
        if canonical in self.ICE_ASPECT:
            if self.astral_fire == 1:
                return 0.9
            if self.astral_fire == 2:
                return 0.8
            if self.astral_fire == 3:
                return 0.7
        return 1.0

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        potency = skill.get("potency", 0)
        return potency * self._aspect_multiplier(canonical), False

    def _apply_action(self, canonical, current_time):
        if canonical in {"Fire", "Fire III", "High Fire II"}:
            stacks = 3 if canonical in {"Fire III", "High Fire II"} else 1
            self._switch_to_astral_fire(stacks, current_time)
        elif canonical in {"Blizzard", "Blizzard III", "High Blizzard II"}:
            stacks = 3 if canonical in {"Blizzard III", "High Blizzard II"} else 1
            self._switch_to_umbral_ice(stacks, current_time)
        elif canonical == "Transpose":
            if self.astral_fire > 0:
                self._switch_to_umbral_ice(1, current_time)
            elif self.umbral_ice > 0:
                self._switch_to_astral_fire(1, current_time)
        elif canonical == "Manafont":
            self.mp = 10000
            self.astral_fire = 3
            self.umbral_ice = 0
            self.umbral_hearts = 3
            self.paradox = 1
            self.thunderhead = 1
            self._refresh_enochian(current_time)
        elif canonical == "Despair":
            self.astral_fire = 3
            self.umbral_ice = 0
            self._refresh_enochian(current_time)
        elif canonical == "Flare":
            self.astral_fire = 3
            self.umbral_ice = 0
            self.umbral_hearts = 0
            self.astral_soul = min(6, self.astral_soul + 3)
            self._refresh_enochian(current_time)
        elif canonical == "Fire IV":
            if self.astral_fire > 0:
                self.astral_soul = min(6, self.astral_soul + 1)
        elif canonical == "Blizzard IV":
            if self.umbral_ice > 0:
                self.umbral_hearts = 3
        elif canonical == "Umbral Soul":
            if self.umbral_ice > 0:
                self.umbral_ice = min(3, self.umbral_ice + 1)
                self.umbral_hearts = min(3, self.umbral_hearts + 1)
                self._refresh_enochian(current_time)
        elif canonical == "Paradox":
            self.paradox = 0
            if self.astral_fire > 0:
                self.firestarter = 1
        elif canonical == "Flare Star":
            if self.astral_soul >= 6:
                self.astral_soul = 0
        elif canonical == "Amplifier":
            self.polyglot = min(3, self.polyglot + 1)
        elif canonical in {"Foul", "Xenoglossy"}:
            if self.polyglot > 0:
                self.polyglot -= 1
        elif canonical in self.THUNDER_SPELLS:
            self.thunderhead = 0
        elif canonical == "Ley Lines":
            self.ley_lines_until = current_time + 20.0
        elif canonical == "Swiftcast":
            self.swiftcast_until = current_time + 10.0
        elif canonical == "Triplecast":
            self.triplecast_stacks = 3
            self.triplecast_until = current_time + 15.7

        if canonical in self.ICE_ASPECT or (canonical == "Transpose" and self.umbral_ice > 0):
            self.mp = 10000
        elif canonical in self.FIRE_MP_COSTS and self.umbral_ice <= 0:
            self.mp = max(0, self.mp - self.FIRE_MP_COSTS[canonical])

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        return None

    def active_damage_buffs(self, t, target_id=None):
        enochian = self._has_enochian(t)
        return {
            "blm_enochian": enochian,
            "blm_astral_fire": self.astral_fire if self.astral_fire and self.enochian_until > t else 0,
            "blm_umbral_ice": self.umbral_ice if self.umbral_ice and self.enochian_until > t else 0,
            "blm_ley_lines": self.ley_lines_until > t,
            "damage_mult": self.ENOCHIAN_MULT if enochian else 1.0,
        }

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        af = active_buffs.get("blm_astral_fire", 0)
        ui = active_buffs.get("blm_umbral_ice", 0)
        if active_buffs.get("blm_enochian"):
            labels.append("天语")
        if af:
            labels.append(f"星火{af}")
        if ui:
            labels.append(f"灵冰{ui}")
        if active_buffs.get("blm_ley_lines"):
            labels.append("黑魔纹")
        if has_potion:
            labels.append("药")
        return labels
