try:
    from .base import JobState
except ImportError:
    from base import JobState


class RdmJobState(JobState):
    EMBOLDEN_DURATION = 20.0
    MANA_GAINS = {
        "Jolt III": (2, 2),
        "Impact": (3, 3),
        "Grand Impact": (3, 3),
        "Verthunder II": (7, 0),
        "Veraero II": (0, 7),
        "Verthunder III": (6, 0),
        "Veraero III": (0, 6),
        "Verfire": (5, 0),
        "Verstone": (0, 5),
        "Verflare": (11, 0),
        "Verholy": (0, 11),
        "Scorch": (4, 4),
        "Resolution": (4, 4),
    }
    ENCHANTED_COSTS = {
        "Enchanted Riposte": (20, 20),
        "Enchanted Zwerchhau": (15, 15),
        "Enchanted Redoublement": (15, 15),
        "Enchanted Moulinet": (20, 20),
        "Enchanted Moulinet Deux": (15, 15),
        "Enchanted Moulinet Trois": (15, 15),
        "Enchanted Reprise": (5, 5),
    }
    SWORDPLAY_SKILLS = set(ENCHANTED_COSTS) - {"Enchanted Reprise"}
    MANA_STACK_GRANTS = SWORDPLAY_SKILLS
    ACCELERATION_SPELLS = {"Verthunder III", "Veraero III", "Impact"}
    MELEE_COMBO_PREV = {
        "Enchanted Zwerchhau": "riposte",
        "Enchanted Redoublement": "zwerchhau",
        "Enchanted Moulinet Deux": "moulinet",
        "Enchanted Moulinet Trois": "moulinet_deux",
    }
    MELEE_COMBO_STEP = {
        "Enchanted Riposte": "riposte",
        "Enchanted Zwerchhau": "zwerchhau",
        "Enchanted Redoublement": "redoublement",
        "Enchanted Moulinet": "moulinet",
        "Enchanted Moulinet Deux": "moulinet_deux",
        "Enchanted Moulinet Trois": "moulinet_trois",
    }
    EMBOLDEN_MAGICAL_DAMAGE_SKILLS = (
        set(MANA_GAINS) | set(ENCHANTED_COSTS) | {"Vice of Thorns", "Prefulgence"}
    )

    def __init__(self):
        super().__init__("RDM")
        self.black_mana = 50
        self.white_mana = 50
        self.mana_stacks = 0
        self.dualcast_until = -1.0
        self.swiftcast_until = -1.0
        self.acceleration_until = -1.0
        self.acceleration_stacks = 0
        self.embolden_start = -1.0
        self.embolden_until = -1.0
        self.thorned_flourish_until = -1.0
        self.magicked_swordplay_until = -1.0
        self.magicked_swordplay_stacks = 0
        self.prefulgence_ready_until = -1.0
        self.grand_impact_ready_until = -1.0
        self.melee_combo_step = None

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {
            "Acceleration", "Embolden", "Manafication", "Swiftcast", "Dualcast",
        }

    def _active(self, until, current_time):
        return until != -1.0 and until > current_time

    def _has_swordplay(self, current_time):
        if not self._active(self.magicked_swordplay_until, current_time):
            self.magicked_swordplay_stacks = 0
        return self.magicked_swordplay_stacks > 0

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        is_ability = not skill.get("is_gcd", False)
        has_base_cast = bool(skill.get("cast", 0))
        hardcast_spell = has_base_cast and snapshot_time > current_time
        state = {"rdm_hardcast_spell": hardcast_spell}

        if canonical != "Swiftcast" and has_base_cast and self._active(self.swiftcast_until, current_time):
            self.swiftcast_until = -1.0
            state["rdm_swiftcast"] = True

        if canonical in self.ACCELERATION_SPELLS and self.acceleration_stacks > 0 and self._active(
                self.acceleration_until, current_time):
            self.acceleration_stacks -= 1
            if self.acceleration_stacks == 0:
                self.acceleration_until = -1.0
            state["rdm_acceleration"] = True

        if not is_ability and self._active(self.dualcast_until, current_time):
            state["rdm_dualcast"] = has_base_cast
            self.dualcast_until = -1.0

        free_swordplay = canonical in self.SWORDPLAY_SKILLS and self._has_swordplay(current_time)
        state["rdm_free_swordplay"] = free_swordplay
        cost = self.ENCHANTED_COSTS.get(canonical)
        if cost and not free_swordplay and (self.black_mana < cost[0] or self.white_mana < cost[1]):
            self.warn("rdm_mana_low", current_time, name,
                      f"{canonical} used with mana B/W={self.black_mana}/{self.white_mana}; expected {cost[0]}/{cost[1]}.")
        expected = self.MELEE_COMBO_PREV.get(canonical)
        if expected:
            state["rdm_melee_combo"] = self.melee_combo_step == expected
        if expected and self.melee_combo_step != expected:
            self.warn("rdm_melee_combo_order", current_time, name,
                      f"{canonical} used while the tracked melee combo expected {expected}.")
        if canonical in {"Verflare", "Verholy"} and self.mana_stacks < 3:
            self.warn("rdm_mana_stack_low", current_time, name,
                      f"{canonical} used with {self.mana_stacks} Mana Stack(s); expected 3.")
        if canonical == "Grand Impact" and not self._active(self.grand_impact_ready_until, current_time):
            self.warn("rdm_grand_impact_not_ready", current_time, name,
                      "Grand Impact used without tracked Grand Impact Ready.")
        if canonical == "Vice of Thorns" and not self._active(self.thorned_flourish_until, current_time):
            self.warn("rdm_thorned_flourish_missing", current_time, name,
                      "Vice of Thorns used without tracked Thorned Flourish.")
        if canonical == "Prefulgence" and not self._active(self.prefulgence_ready_until, current_time):
            self.warn("rdm_prefulgence_not_ready", current_time, name,
                      "Prefulgence used without tracked Prefulgence Ready.")
        return state

    def on_press_complete(self, name, current_time):
        self._apply_press_complete(name, current_time, None)

    def _apply_press_complete(self, name, current_time, skill):
        canonical = self._canonical(name)
        if canonical == "Acceleration":
            self.acceleration_stacks = 1
            self.acceleration_until = current_time + 20.0
            self.grand_impact_ready_until = current_time + 30.0
        elif canonical == "Embolden":
            self.embolden_start, self.embolden_until = self.party_buff_window(
                canonical, skill, current_time, self.EMBOLDEN_DURATION
            )
            self.thorned_flourish_until = current_time + 30.0
        elif canonical == "Manafication":
            self.magicked_swordplay_stacks = 3
            self.magicked_swordplay_until = current_time + 30.0
            self.prefulgence_ready_until = current_time + 30.0
            self.combo_action = None
            self.melee_combo_step = None
        elif canonical == "Swiftcast":
            self.swiftcast_until = current_time + 10.0

    def on_press_confirmed(self, name, skill, current_time, payload):
        self._apply_press_complete(self._canonical(name, skill), current_time, skill)

    def effective_cast_time(self, name, skill, event, current_time, default_cast_time):
        if event and event.get("cast_time") is not None:
            return default_cast_time
        if default_cast_time <= 0 or not skill.get("cast", 0):
            return default_cast_time
        canonical = self._canonical(name, skill)
        if self._active(self.swiftcast_until, current_time):
            return 0.0
        if self._active(self.dualcast_until, current_time):
            return 0.0
        if canonical in self.ACCELERATION_SPELLS and self.acceleration_stacks > 0 and self._active(
                self.acceleration_until, current_time):
            return 0.0
        return default_cast_time

    def resolve_potency(self, name, skill, current_time, payload):
        potency, is_combo = super().resolve_potency(name, skill, current_time, payload)
        canonical = self._canonical(name, skill)
        if canonical in self.MELEE_COMBO_PREV and "rdm_melee_combo" in payload:
            is_combo = bool(payload.get("rdm_melee_combo"))
            potency = skill.get("potency" if is_combo else "base_potency", potency)
        if canonical == "Impact" and payload.get("rdm_acceleration"):
            potency += 50
        return potency, is_combo

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        cost = self.ENCHANTED_COSTS.get(canonical)
        if cost:
            if payload.get("rdm_free_swordplay"):
                self.magicked_swordplay_stacks = max(0, self.magicked_swordplay_stacks - 1)
                if self.magicked_swordplay_stacks == 0:
                    self.magicked_swordplay_until = -1.0
            else:
                self.black_mana = max(0, self.black_mana - cost[0])
                self.white_mana = max(0, self.white_mana - cost[1])
        if canonical in self.MANA_STACK_GRANTS:
            self.mana_stacks = min(3, self.mana_stacks + 1)
        elif canonical in {"Verflare", "Verholy"}:
            self.mana_stacks = max(0, self.mana_stacks - 3)

        if canonical in self.MELEE_COMBO_STEP:
            self.melee_combo_step = self.MELEE_COMBO_STEP[canonical]
        elif canonical not in {"Manafication"} and skill.get("is_gcd", False):
            self.melee_combo_step = None

        black_gain, white_gain = self.MANA_GAINS.get(canonical, (0, 0))
        self.black_mana = min(100, self.black_mana + black_gain)
        self.white_mana = min(100, self.white_mana + white_gain)

        if payload.get("rdm_hardcast_spell"):
            self.dualcast_until = current_time + 15.0
        if canonical == "Grand Impact":
            self.grand_impact_ready_until = -1.0
        elif canonical == "Vice of Thorns":
            self.thorned_flourish_until = -1.0
        elif canonical == "Prefulgence":
            self.prefulgence_ready_until = -1.0

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        embolden = self._active_window(self.embolden_start, self.embolden_until, t)
        dualcast = self._active(self.dualcast_until, t)
        if embolden:
            damage_mult *= 1.10
        swordplay = self._has_swordplay(t)
        return {
            "rdm_embolden": embolden,
            "rdm_manafication": swordplay,
            "rdm_dualcast": dualcast,
            "damage_mult": damage_mult,
            "damage_factors": [("鼓励", 1.10)] if embolden else [],
            "auto_damage_mult": 1.0,
        }

    def filter_active_damage_buffs(self, name, skill, active_buffs):
        if not active_buffs.get("rdm_embolden"):
            return active_buffs
        if self._canonical(name, skill) in self.EMBOLDEN_MAGICAL_DAMAGE_SKILLS:
            return active_buffs
        filtered = dict(active_buffs)
        filtered["rdm_embolden"] = False
        filtered["damage_mult"] = filtered.get("damage_mult", 1.0) / 1.10
        filtered["damage_factors"] = [
            factor for factor in filtered.get("damage_factors", []) if factor[0] != "鼓励"
        ]
        return filtered

    def allows_auto_attacks(self, job_profile):
        return True

    def should_start_auto_attacks(self, name, skill, current_time):
        return self._canonical(name, skill).startswith("Enchanted ")

    def auto_attack_interval_multiplier(self, t):
        # ponytail: retained xivintheshell RDM axes use this caster AA cadence; replace with melee-range windows if axes expose position.
        return 3.44 / 2.64

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("rdm_embolden"):
            labels.append("鼓励")
        if active_buffs.get("rdm_manafication"):
            labels.append("魔元")
        if active_buffs.get("rdm_dualcast"):
            labels.append("连续")
        if has_potion:
            labels.append("药")
        return labels
