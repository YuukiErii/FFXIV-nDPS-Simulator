try:
    from .base import JobState
except ImportError:
    from base import JobState


class DncJobState(JobState):
    STEP_ACTIONS = {"Emboite", "Entrechat", "Jete", "Pirouette"}
    STANDARD_POTENCY = {0: 360, 1: 540, 2: 850}
    STANDARD_MULT = {0: 1.0, 1: 1.02, 2: 1.05}
    TECHNICAL_POTENCY = {0: 350, 1: 540, 2: 720, 3: 900, 4: 1300}
    TECHNICAL_MULT = {0: 1.0, 1: 1.01, 2: 1.02, 3: 1.03, 4: 1.05}
    ESPRIT_GAUGE_GCDS = {
        "Cascade", "Fountain", "Reverse Cascade", "Fountainfall",
        "Windmill", "Bladeshower", "Rising Windmill", "Bloodshower",
    }

    def __init__(self):
        super().__init__("DNC")
        self.standard_until = -1.0
        self.standard_mult = 1.0
        self.technical_until = -1.0
        self.technical_mult = 1.0
        self.devilment_until = -1.0
        self.esprit_self_until = -1.0
        self.last_dance_ready_until = -1.0
        self.finishing_ready_until = -1.0
        self.flourishing_finish_until = -1.0
        self.dawn_ready_until = -1.0
        self.starfall_ready_until = -1.0
        self.dance_mode = None
        self.steps = 0
        self.esprit = 0
        self.fan3_ready = 0
        self.fan4_ready = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        canonical = self._canonical(name, skill)
        return (
            "Standard Finish" in canonical
            or "Technical Finish" in canonical
            or canonical in {"Finishing Move", "Tillana", "Devilment"}
        )

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        if canonical in self.STEP_ACTIONS and not self.dance_mode:
            self.warn("dnc_step_without_dance", current_time, name,
                      f"{canonical} used outside a tracked dance step sequence.")
        if "Standard Finish" in canonical:
            if self.dance_mode != "standard" or self.steps < 2:
                self.warn("dnc_standard_finish_steps_low", current_time, name,
                          f"{canonical} used with {self.steps} tracked standard steps; expected 2.")
        return {}

    def _finish_steps(self, canonical, cap):
        if canonical.startswith("Single "):
            return 1
        if canonical.startswith("Double "):
            return 2
        if canonical.startswith("Triple "):
            return 3
        if canonical.startswith("Quadruple "):
            return 4
        if canonical == "Technical Finish":
            return 4
        return min(cap, max(0, self.steps))

    def _spend_esprit(self, amount):
        if self.esprit < amount:
            self.esprit = amount
        self.esprit -= amount

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if "Standard Finish" in canonical:
            return self.STANDARD_POTENCY[self._finish_steps(canonical, 2)], False
        if "Technical Finish" in canonical:
            return self.TECHNICAL_POTENCY[self._finish_steps(canonical, 4)], False
        return super().resolve_potency(name, skill, current_time, payload)

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Standard Step":
            self.dance_mode = "standard"
            self.steps = 0
        elif canonical == "Technical Step":
            self.dance_mode = "technical"
            self.steps = 0
        elif canonical in self.STEP_ACTIONS and self.dance_mode:
            self.steps = min(4 if self.dance_mode == "technical" else 2, self.steps + 1)
        elif "Standard Finish" in canonical:
            steps = self._finish_steps(canonical, 2)
            self.standard_until = current_time + 60.0
            self.standard_mult = self.STANDARD_MULT[steps]
            self.esprit_self_until = max(self.esprit_self_until, current_time + 60.0)
            self.last_dance_ready_until = current_time + 30.0
            self.dance_mode = None
            self.steps = 0
        elif canonical == "Finishing Move":
            self.standard_until = current_time + 60.0
            self.standard_mult = 1.05
            self.esprit_self_until = max(self.esprit_self_until, current_time + 60.0)
            self.last_dance_ready_until = current_time + 30.0
            self.finishing_ready_until = -1.0
            self.dance_mode = None
        elif "Technical Finish" in canonical:
            steps = self._finish_steps(canonical, 4)
            self.technical_until = current_time + 20.45
            self.technical_mult = self.TECHNICAL_MULT[steps]
            self.esprit_self_until = max(self.esprit_self_until, current_time + 20.45)
            self.flourishing_finish_until = current_time + 30.0
            self.dawn_ready_until = current_time + 30.0
            self.dance_mode = None
            self.steps = 0
        elif canonical == "Tillana":
            self.esprit = min(100, self.esprit + 50)
            self.flourishing_finish_until = -1.0
        elif canonical == "Devilment":
            self.devilment_until = current_time + 20.0
            self.starfall_ready_until = current_time + 20.0
        elif canonical == "Flourish":
            self.fan3_ready = max(self.fan3_ready, 1)
            self.fan4_ready = max(self.fan4_ready, 1)
            self.finishing_ready_until = current_time + 30.0
        elif canonical in self.ESPRIT_GAUGE_GCDS and self.esprit_self_until > current_time:
            self.esprit = min(100, self.esprit + 5)
        elif canonical in {"Saber Dance", "Dance of the Dawn"}:
            self._spend_esprit(50)
            if canonical == "Dance of the Dawn":
                self.dawn_ready_until = -1.0
        elif canonical == "Last Dance":
            self.last_dance_ready_until = -1.0
        elif canonical == "Starfall Dance":
            self.starfall_ready_until = -1.0
        elif canonical == "Fan Dance":
            self.fan3_ready = max(self.fan3_ready, 1)
        elif canonical == "Fan Dance III":
            self.fan3_ready = max(0, self.fan3_ready - 1)
        elif canonical == "Fan Dance IV":
            self.fan4_ready = max(0, self.fan4_ready - 1)

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        damage_factors = []
        if self.standard_until > t:
            damage_mult *= self.standard_mult
            damage_factors.append(("标准舞", self.standard_mult))
        if self.technical_until > t:
            damage_mult *= self.technical_mult
            damage_factors.append(("技巧舞", self.technical_mult))
        return {
            "dnc_standard": self.standard_until > t,
            "dnc_technical": self.technical_until > t,
            "dnc_devilment": self.devilment_until > t,
            "damage_mult": damage_mult,
            "damage_factors": damage_factors,
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
