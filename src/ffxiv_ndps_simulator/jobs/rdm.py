try:
    from .base import JobState
except ImportError:
    from base import JobState


class RdmJobState(JobState):
    BLACK_MANA = {
        "Verthunder III", "Verthunder II", "Verfire", "Verflare",
        "Impact", "Jolt III", "Scorch", "Resolution",
    }
    WHITE_MANA = {
        "Veraero III", "Veraero II", "Verstone", "Verholy",
        "Jolt III", "Scorch", "Resolution",
    }

    def __init__(self):
        super().__init__("RDM")
        self.black_mana = 50
        self.white_mana = 50
        self.dualcast_until = -1.0
        self.acceleration_until = -1.0
        self.acceleration_stacks = 0
        self.embolden_until = -1.0
        self.manafication_until = -1.0
        self.melee_combo_step = None

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Acceleration", "Embolden", "Manafication"}

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        if skill.get("cast", 0) and self.dualcast_until > snapshot_time:
            self.dualcast_until = -1.0
        if self.acceleration_stacks > 0 and self.acceleration_until > snapshot_time and canonical in {
            "Verthunder III", "Veraero III", "Impact",
        }:
            self.acceleration_stacks -= 1
            return {"guaranteed_crit": False}
        if canonical.startswith("Enchanted ") and (self.black_mana < 20 or self.white_mana < 20):
            self.warn("rdm_mana_low", current_time, name,
                      f"{canonical} used with mana B/W={self.black_mana}/{self.white_mana}.")
        if canonical == "Enchanted Zwerchhau" and self.melee_combo_step != "riposte":
            self.warn("rdm_melee_combo_order", current_time, name,
                      "Enchanted Zwerchhau used without prior Enchanted Riposte.")
        elif canonical == "Enchanted Redoublement" and self.melee_combo_step != "zwerchhau":
            self.warn("rdm_melee_combo_order", current_time, name,
                      "Enchanted Redoublement used without prior Enchanted Zwerchhau.")
        return {}

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Acceleration":
            self.acceleration_stacks = 1
            self.acceleration_until = current_time + 20.0
        elif canonical == "Embolden":
            self.embolden_until = current_time + 19.95
        elif canonical == "Manafication":
            self.manafication_until = current_time + 30.0
            self.black_mana = min(100, self.black_mana + 50)
            self.white_mana = min(100, self.white_mana + 50)
        elif canonical.startswith("Enchanted "):
            self.black_mana = max(0, self.black_mana - 20)
            self.white_mana = max(0, self.white_mana - 20)
            if canonical == "Enchanted Riposte":
                self.melee_combo_step = "riposte"
            elif canonical == "Enchanted Zwerchhau":
                self.melee_combo_step = "zwerchhau"
            elif canonical == "Enchanted Redoublement":
                self.melee_combo_step = "redoublement"
        else:
            if canonical in self.BLACK_MANA:
                self.black_mana = min(100, self.black_mana + 5)
            if canonical in self.WHITE_MANA:
                self.white_mana = min(100, self.white_mana + 5)
            if skill.get("cast", 0) == 0 and skill.get("potency", 0) > 0:
                self.dualcast_until = current_time + 15.0

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        if self.embolden_until > t:
            damage_mult *= 1.05
        if self.manafication_until > t:
            damage_mult *= 1.05
        return {
            "rdm_embolden": self.embolden_until > t,
            "rdm_manafication": self.manafication_until > t,
            "rdm_dualcast": self.dualcast_until > t,
            "damage_mult": damage_mult,
        }

    def allows_auto_attacks(self, job_profile):
        return True

    def should_start_auto_attacks(self, name, skill, current_time):
        return self._canonical(name, skill).startswith("Enchanted ")

    def auto_attack_interval_multiplier(self, t):
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
