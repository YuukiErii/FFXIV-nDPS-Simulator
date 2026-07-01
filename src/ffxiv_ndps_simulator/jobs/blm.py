try:
    from .base import JobState
except ImportError:
    from base import JobState


class BlmJobState(JobState):
    ENOCHIAN_MULT = 1.27
    # ponytail: Patch 7.2 removed AF/UI expiration; keep the state until an action swaps/removes it.
    ELEMENT_TIMEOUT = float("inf")
    POLYGLOT_INTERVAL = 30.0

    FIRE_ASPECT = {
        "Fire", "Fire II", "Fire III", "Fire IV", "High Fire II",
        "Despair", "Flare", "Flare Star",
    }
    ICE_ASPECT = {
        "Blizzard", "Blizzard II", "Blizzard III", "Blizzard IV", "High Blizzard II", "Freeze",
    }
    THUNDER_SPELLS = {
        "Thunder", "Thunder II", "Thunder III", "Thunder IV",
        "High Thunder", "High Thunder II",
    }
    FIRE_MP_COSTS = {
        "Fire": 800,
        "Fire II": 1500,
        "Fire III": 2000,
        "Fire IV": 800,
        "High Fire II": 1500,
    }
    ALL_MP_SPELLS = {"Despair", "Flare"}
    UI_MP_RESTORE = {1: 2500, 2: 5000, 3: 10000}

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
        self.enochian_until = float("-inf")
        self.ley_lines_until = float("-inf")
        self.swiftcast_until = float("-inf")
        self.triplecast_stacks = 0
        self.triplecast_until = float("-inf")
        self.next_polyglot_at = float("-inf")
        self._pending_canonical = None
        self._pending_mp_spend = (0, 0, False, False)
        self._pending_umbral_restore = 0

    def _canonical(self, name, skill=None):
        if skill:
            return skill.get("amas_name") or skill.get("canonical_name") or name
        return name

    def _refresh_enochian(self, current_time):
        if self.enochian_until <= current_time or self.next_polyglot_at < 0:
            self.next_polyglot_at = current_time + self.POLYGLOT_INTERVAL
        self.enochian_until = current_time + self.ELEMENT_TIMEOUT

    def _has_enochian(self, current_time):
        return self.enochian_until > current_time and (self.astral_fire > 0 or self.umbral_ice > 0)

    def advance_time(self, current_time):
        super().advance_time(current_time)
        if not self._has_enochian(current_time):
            if self.enochian_until <= current_time:
                self.astral_fire = 0
                self.umbral_ice = 0
                self.astral_soul = 0
                self.next_polyglot_at = -1.0
            return
        if self.next_polyglot_at < 0:
            self.next_polyglot_at = current_time + self.POLYGLOT_INTERVAL
        while self.next_polyglot_at <= current_time and self.next_polyglot_at <= self.enochian_until:
            self.polyglot = min(3, self.polyglot + 1)
            self.next_polyglot_at += self.POLYGLOT_INTERVAL

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

    def _consume_instant_cast_status(self, canonical, current_time):
        if canonical == "Fire III" and self.firestarter > 0:
            self.firestarter = 0
            return
        if canonical in {"Despair", "Foul", "Xenoglossy", "Paradox", "Umbral Soul"}:
            return
        if self.swiftcast_until > current_time:
            self.swiftcast_until = -1.0
            return
        self.swiftcast_until = -1.0
        if self.triplecast_until <= current_time:
            self.triplecast_stacks = 0
        elif self.triplecast_stacks > 0:
            self.triplecast_stacks -= 1

    def _mp_spend_for(self, canonical):
        if canonical == "Fire III" and self.firestarter > 0:
            return 0, 0, False, False
        if canonical == "Paradox":
            if self.umbral_ice > 0:
                return 0, 0, False, False
            return 1600, 1600, False, False
        if canonical == "Flare" and self.umbral_hearts > 0:
            if self.umbral_ice > 0:
                return 0, 0, False, False
            return 800, (self.mp * 2 + 2) // 3, False, False
        if canonical in self.ALL_MP_SPELLS:
            if self.umbral_ice > 0:
                return 0, 0, False, False
            return 800, self.mp, False, True
        base_cost = self.FIRE_MP_COSTS.get(canonical, 0)
        if not base_cost or self.umbral_ice > 0:
            return 0, 0, False, False
        spend = base_cost
        consumes_heart = False
        if canonical in self.FIRE_ASPECT and self.astral_fire > 0:
            if self.umbral_hearts > 0:
                consumes_heart = True
            else:
                spend = base_cost * 2
        return spend, spend, consumes_heart, False

    def _apply_pending_mp_spend(self):
        _required, spend, consumes_heart, all_mp = self._pending_mp_spend
        self._pending_mp_spend = (0, 0, False, False)
        if all_mp:
            self.mp = 0
        elif spend:
            self.mp = max(0, self.mp - spend)
        if consumes_heart:
            self.umbral_hearts = max(0, self.umbral_hearts - 1)

    def handles_skill_buff(self, name, skill):
        return bool(skill.get("buff"))

    def confirms_at_snapshot(self, name, skill):
        return True

    def on_press(self, name, skill, current_time, snapshot_time):
        self.advance_time(current_time)
        canonical = self._canonical(name, skill)
        self._pending_canonical = canonical
        if canonical in {"Fire IV", "Despair", "Flare", "Flare Star"} and self.astral_fire <= 0:
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
        self._pending_mp_spend = self._mp_spend_for(canonical)
        self._pending_umbral_restore = (
            self.UI_MP_RESTORE.get(self.umbral_ice, 0)
            if canonical in self.ICE_ASPECT or canonical == "Umbral Soul"
            else 0
        )
        mp_required = self._pending_mp_spend[0]
        if mp_required and self.mp < mp_required:
            self.warn("blm_mp_low", current_time, name,
                      f"{canonical} used with MP {self.mp}; expected at least {mp_required}.")
        if skill.get("cast", 0) or canonical in self.FIRE_ASPECT or canonical in self.ICE_ASPECT:
            self._consume_instant_cast_status(canonical, current_time)
        return {
            "snapshot_potency": skill.get("potency", 0) * self._aspect_multiplier(canonical),
        }

    def on_press_complete(self, name, current_time):
        self.advance_time(current_time)
        canonical = self._pending_canonical or name
        self._pending_canonical = None
        self._apply_action(canonical, current_time)

    def effective_cast_time(self, name, skill, event, current_time, default_cast_time):
        if event and event.get("cast_time") is not None:
            return default_cast_time
        canonical = self._canonical(name, skill)
        if canonical in self.THUNDER_SPELLS:
            return 0.0
        if canonical == "Fire III" and self.firestarter > 0:
            return 0.0
        if canonical in {"Despair", "Foul", "Xenoglossy", "Paradox", "Umbral Soul"}:
            return 0.0
        if self.swiftcast_until > current_time:
            return 0.0
        if self.triplecast_stacks > 0 and self.triplecast_until > current_time:
            return 0.0
        cast_time = default_cast_time
        if cast_time > 0:
            if canonical in self.ICE_ASPECT and self.astral_fire >= 3:
                cast_time *= 0.5
            elif canonical in self.FIRE_ASPECT and self.umbral_ice >= 3:
                cast_time *= 0.5
            if self.ley_lines_until > current_time:
                cast_time *= 0.85
        return cast_time

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
        if "snapshot_potency" in payload:
            return payload["snapshot_potency"], False
        canonical = self._canonical(name, skill)
        potency = skill.get("potency", 0)
        return potency * self._aspect_multiplier(canonical), False

    def _apply_action(self, canonical, current_time):
        if canonical in {"Fire", "Fire II", "Fire III", "High Fire II"}:
            stacks = 3 if canonical in {"Fire II", "Fire III", "High Fire II"} else 1
            self._switch_to_astral_fire(stacks, current_time)
        elif canonical in {"Blizzard", "Blizzard II", "Blizzard III", "High Blizzard II"}:
            stacks = 3 if canonical in {"Blizzard II", "Blizzard III", "High Blizzard II"} else 1
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
        elif canonical == "Freeze":
            if self.umbral_ice > 0:
                self.umbral_hearts = 3
        elif canonical == "Umbral Soul":
            if self.umbral_ice > 0:
                self.umbral_ice = min(3, self.umbral_ice + 1)
                self.umbral_hearts = min(3, self.umbral_hearts + 1)
                self._refresh_enochian(current_time)
        elif canonical == "Paradox":
            if self.astral_fire > 0 or self.umbral_ice > 0:
                self._refresh_enochian(current_time)
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
            self.triplecast_until = current_time + 15.0

        self._apply_pending_mp_spend()
        if self._pending_umbral_restore:
            self.gain_mp(self._pending_umbral_restore)
        self._pending_umbral_restore = 0

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        return None

    def _dot_target_ids(self, target_count, target_id):
        raw_ids = self._event_context.get("target_ids") or []
        ids = []
        for raw_id in raw_ids if isinstance(raw_ids, (list, tuple)) else []:
            try:
                tid = int(raw_id)
            except (TypeError, ValueError):
                continue
            if tid > 0 and tid not in ids:
                ids.append(tid)

        if not ids:
            ids.append(int(target_id or 1))
            candidate = 1
            while len(ids) < max(1, int(target_count or 1)):
                if candidate not in ids:
                    ids.append(candidate)
                candidate += 1

        return ids[:max(1, int(target_count or 1))]

    def dot_applications(self, name, skill, current_time, target_count, target_id,
                         active_buffs, has_potion):
        canonical = self._canonical(name, skill)
        if (
            canonical not in {"Thunder IV", "High Thunder II"}
            or skill.get("dot_primary_only", True)
            or not (self._event_context.get("multi_boss_mode") or self._event_context.get("target_ids"))
        ):
            return super().dot_applications(
                name, skill, current_time, target_count, target_id, active_buffs, has_potion
            )

        return [
            {
                "name": skill.get("dot_name", name),
                "source_name": name,
                "dot_key": name,
                "tid": tid,
                "targets": 1,
                "potency": skill["dot_potency"],
                "buffs": active_buffs,
                "expire": current_time + skill["dot_duration"],
                "has_potion": has_potion,
                "guaranteed_crit": skill.get("dot_guaranteed_crit", False),
                "guaranteed_dh": skill.get("dot_guaranteed_dh", False),
            }
            for tid in self._dot_target_ids(target_count, target_id)
        ]

    def active_damage_buffs(self, t, target_id=None):
        enochian = self._has_enochian(t)
        return {
            "blm_enochian": enochian,
            "blm_astral_fire": self.astral_fire if self.astral_fire and self.enochian_until > t else 0,
            "blm_umbral_ice": self.umbral_ice if self.umbral_ice and self.enochian_until > t else 0,
            "blm_ley_lines": self.ley_lines_until > t,
            "damage_mult": self.ENOCHIAN_MULT if enochian else 1.0,
            "damage_factors": [("天语", self.ENOCHIAN_MULT)] if enochian else [],
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
