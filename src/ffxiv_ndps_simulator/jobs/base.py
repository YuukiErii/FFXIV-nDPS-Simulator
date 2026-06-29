class JobState:
    def __init__(self, job):
        self.job = job
        self.combo_action = None
        self.combo_time = -1.0
        self.resource_warnings = []
        self._event_context = {}

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

    def on_press(self, name, skill, current_time, snapshot_time):
        return {}

    def on_press_complete(self, name, current_time):
        return None

    def on_press_confirmed(self, name, skill, current_time, payload):
        return self.on_press_complete(name, current_time)

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

    def followup_damage_events(self, name, skill, current_time, payload):
        return []

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

    def auto_attack_interval_multiplier(self, t):
        return 1.0

    def allows_auto_attacks(self, job_profile):
        return not getattr(job_profile, "is_caster", False)

    def should_start_auto_attacks(self, name, skill, current_time):
        return True

    def can_activate_without_target(self, name, skill):
        return False

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
