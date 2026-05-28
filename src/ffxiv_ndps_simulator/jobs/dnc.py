try:
    from .base import JobState
except ImportError:
    from base import JobState


class DncJobState(JobState):
    def __init__(self):
        super().__init__("DNC")
        self.standard_until = -1.0
        self.technical_until = -1.0
        self.devilment_until = -1.0
        self.dance_mode = None
        self.steps = 0
        self.esprit = 0
        self.fan3_ready = 0
        self.fan4_ready = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {
            "Standard Finish", "Double Standard Finish", "Technical Finish",
            "Quadruple Technical Finish", "Finishing Move", "Tillana", "Devilment",
        }

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        if canonical in {"Emboite", "Entrechat", "Jete", "Pirouette"} and not self.dance_mode:
            self.warn("dnc_step_without_dance", current_time, name,
                      f"{canonical} used outside a tracked dance step sequence.")
        if "Standard Finish" in canonical:
            if self.dance_mode != "standard" or self.steps < 2:
                self.warn("dnc_standard_finish_steps_low", current_time, name,
                          f"{canonical} used with {self.steps} tracked standard steps; expected 2.")
        if "Technical Finish" in canonical:
            if self.dance_mode != "technical" or self.steps < 4:
                self.warn("dnc_technical_finish_steps_low", current_time, name,
                          f"{canonical} used with {self.steps} tracked technical steps; expected 4.")
        if canonical == "Finishing Move" and self.standard_until <= snapshot_time:
            self.warn("dnc_finishing_move_not_ready", current_time, name,
                      "Finishing Move used without a tracked Standard Finish buff.")
        if canonical == "Fan Dance III" and self.fan3_ready <= 0:
            self.warn("dnc_fan3_not_ready", current_time, name,
                      "Fan Dance III used without a tracked Flourish/Fan Dance proc.")
        if canonical == "Fan Dance IV" and self.fan4_ready <= 0:
            self.warn("dnc_fan4_not_ready", current_time, name,
                      "Fan Dance IV used without a tracked Flourish proc.")
        if canonical == "Saber Dance" and self.esprit < 50:
            self.warn("dnc_esprit_low", current_time, name,
                      f"Saber Dance used with Esprit {self.esprit}; expected at least 50.")
        return {}

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Standard Step":
            self.dance_mode = "standard"
            self.steps = 0
        elif canonical == "Technical Step":
            self.dance_mode = "technical"
            self.steps = 0
        elif canonical in {"Emboite", "Entrechat", "Jete", "Pirouette"} and self.dance_mode:
            self.steps += 1
        elif "Standard Finish" in canonical or canonical == "Finishing Move":
            self.standard_until = current_time + 60.0
            self.dance_mode = None
        elif "Technical Finish" in canonical or canonical == "Tillana":
            self.technical_until = current_time + 20.5
            self.dance_mode = None
        elif canonical == "Devilment":
            self.devilment_until = current_time + 20.0
        elif canonical == "Flourish":
            self.steps = 0
            self.fan3_ready = max(self.fan3_ready, 1)
            self.fan4_ready = max(self.fan4_ready, 1)
        elif canonical in {"Cascade", "Fountain", "Reverse Cascade", "Fountainfall",
                           "Windmill", "Bladeshower", "Rising Windmill", "Bloodshower",
                           "Last Dance", "Tillana"}:
            self.esprit = min(100, self.esprit + 5)
        elif canonical == "Saber Dance":
            self.esprit = max(0, self.esprit - 50)
        elif canonical == "Fan Dance":
            self.fan3_ready = max(self.fan3_ready, 1)
        elif canonical == "Fan Dance III":
            self.fan3_ready = max(0, self.fan3_ready - 1)
        elif canonical == "Fan Dance IV":
            self.fan4_ready = max(0, self.fan4_ready - 1)

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        if self.standard_until > t:
            damage_mult *= 1.05
        if self.technical_until > t:
            damage_mult *= 1.05
        return {
            "dnc_standard": self.standard_until > t,
            "dnc_technical": self.technical_until > t,
            "dnc_devilment": self.devilment_until > t,
            "damage_mult": damage_mult,
            "crit_rate_add": 0.20 if self.devilment_until > t else 0.0,
            "dh_rate_add": 0.20 if self.devilment_until > t else 0.0,
        }

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("dnc_standard"):
            labels.append("标准舞")
        if active_buffs.get("dnc_technical"):
            labels.append("技巧舞")
        if active_buffs.get("dnc_devilment"):
            labels.append("伶俐")
        if has_potion:
            labels.append("药")
        return labels
