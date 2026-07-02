class JobState:
    MAX_MP = 10000
    MP_TICK_INTERVAL = 3.0
    BASE_MP_TICK = 200
    LUCID_DREAMING_MP_TICK = 550
    LUCID_DREAMING_DURATION = 21.0

    def __init__(self, job):
        self.job = job
        self.combo_action = None
        self.combo_time = -1.0
        self.resource_warnings = []
        self._event_context = {}
        self.next_mana_tick_at = None
        self.lucid_dreaming_until = -1.0

    def set_event_context(self, payload):
        self._event_context = dict(payload or {})

    def warn(self, code, current_time, skill_name, message, severity="warning", row_no=None):
        warning = {
            "job": self.job,
            "code": code,
            "time": round(float(current_time), 3),
            "skill": skill_name,
            "severity": severity,
            "message": message,
        }
        if row_no is None:
            row_no = self._event_context.get("row_no")
        if row_no is not None:
            warning["row_no"] = row_no
        self.resource_warnings.append(warning)

    def get_resource_warnings(self):
        return list(self.resource_warnings)

    def resource_state(self):
        """Return the serializable job state needed by post-run window reports."""
        hidden = {"resource_warnings", "_event_context"}

        def clean(value):
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            if isinstance(value, dict):
                return {str(key): clean(item) for key, item in value.items()}
            if isinstance(value, (list, tuple, set)):
                return [clean(item) for item in value]
            return str(value)

        state = {}
        for key, value in vars(self).items():
            if key in hidden or key.startswith("_"):
                continue
            state[key] = clean(value)
        return state

    def configure_mana_ticks(self, first_tick):
        self.next_mana_tick_at = None if first_tick is None else float(first_tick)

    def advance_time(self, current_time):
        while self.next_mana_tick_at is not None and self.next_mana_tick_at <= current_time + 1e-9:
            self.on_mana_tick(self.next_mana_tick_at)
            self.next_mana_tick_at += self.MP_TICK_INTERVAL

    def gain_mp(self, amount):
        if hasattr(self, "mp"):
            self.mp = min(self.MAX_MP, self.mp + int(amount))

    def on_mana_tick(self, tick_time):
        self.gain_mp(self.BASE_MP_TICK)
        if self.lucid_dreaming_until >= tick_time - 1e-9:
            self.gain_mp(self.LUCID_DREAMING_MP_TICK)

    def on_common_action_confirmed(self, name, skill, current_time):
        canonical = (skill or {}).get("amas_name") or (skill or {}).get("canonical_name") or name
        if canonical in {"Lucid Dreaming", "醒梦"}:
            self.lucid_dreaming_until = max(self.lucid_dreaming_until, current_time + self.LUCID_DREAMING_DURATION)

    @staticmethod
    def _active_until(until, current_time):
        return until != -1.0 and until > current_time

    def on_press(self, name, skill, current_time, snapshot_time):
        return {}

    def on_press_complete(self, name, current_time):
        return None

    def on_press_confirmed(self, name, skill, current_time, payload):
        self.on_common_action_confirmed(name, skill, current_time)
        return self.on_press_complete(name, current_time)

    def confirms_at_snapshot(self, name, skill):
        return False

    def handles_skill_buff(self, name, skill):
        return False

    def consume_combo_override(self, name, skill, current_time):
        return False

    def is_combo(self, name, skill, current_time, payload):
        combo_prev = skill.get("combo_prev")
        if not combo_prev:
            return False
        return self.combo_action in combo_prev and (current_time - self.combo_time < 30)

    def resolve_potency(self, name, skill, current_time, payload):
        is_combo = self.is_combo(name, skill, current_time, payload)
        if "base_potency" in skill and not is_combo:
            return skill.get("base_potency", 0), is_combo
        return skill.get("potency", 0), is_combo

    @staticmethod
    def _updates_combo_state(skill, payload):
        event_is_gcd = payload.get("is_gcd")
        if event_is_gcd is not None:
            return bool(event_is_gcd)
        skill_is_gcd = skill.get("is_gcd")
        if skill_is_gcd is not None:
            return bool(skill_is_gcd)
        return bool(skill.get("combo_prev"))

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        if self._updates_combo_state(skill, payload):
            self.combo_action = name
            self.combo_time = current_time
        return None

    def should_resolve_damage(self, name, skill, current_time, payload):
        return True

    def followup_damage_events(self, name, skill, current_time, payload):
        return []

    def is_followup_active(self, payload, current_time):
        return True

    def dot_applications(self, name, skill, current_time, target_count, target_id, active_buffs, has_potion):
        if "dot_potency" not in skill:
            return []
        dot_targets = 1 if skill.get("dot_primary_only", True) else target_count
        return [{
            "name": skill.get("dot_name", name),
            "source_name": name,
            "dot_key": name,
            "tid": target_id,
            "targets": dot_targets,
            "potency": skill["dot_potency"],
            "buffs": active_buffs,
            "expire": current_time + skill["dot_duration"],
            "has_potion": has_potion,
            "guaranteed_crit": skill.get("dot_guaranteed_crit", False),
            "guaranteed_dh": skill.get("dot_guaranteed_dh", False),
        }]

    def active_damage_buffs(self, t, target_id=None):
        return {}

    def filter_active_damage_buffs(self, name, skill, active_buffs):
        return active_buffs

    def auto_attack_interval_multiplier(self, t):
        return 1.0

    def allows_auto_attacks(self, job_profile):
        return not getattr(job_profile, "is_caster", False)

    def allows_auto_attack_at(self, current_time):
        return True

    def should_start_auto_attacks(self, name, skill, current_time):
        return bool(skill.get("potency", 0) or skill.get("dot_potency", 0))

    def can_activate_without_target(self, name, skill):
        return False

    def effective_cast_time(self, name, skill, event, current_time, default_cast_time):
        return default_cast_time

    def is_dot_active(self, dot, current_time):
        return True

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("damage_mult", 1.0) > 1.0001:
            labels.append("增伤")
        if active_buffs.get("crit_rate_add", 0.0) > 0:
            labels.append("暴击")
        if active_buffs.get("dh_rate_add", 0.0) > 0:
            labels.append("直击")
        if has_potion:
            labels.append("药")
        return labels
