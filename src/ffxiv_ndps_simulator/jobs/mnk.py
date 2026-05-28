try:
    from .base import JobState
except ImportError:
    from base import JobState


class MnkJobState(JobState):
    def __init__(self):
        super().__init__("MNK")
        self.form = "opo"
        self.form_until = 30.0
        self.perfect_balance_stacks = 0
        self.perfect_balance_until = -1.0
        self.riddle_fire_until = -1.0
        self.brotherhood_until = -1.0
        self.riddle_wind_until = -1.0
        self.chakra = 0
        self.pb_consumed = 0
        self.blitz_ready = False

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Riddle of Fire", "Brotherhood", "Riddle of Wind", "Perfect Balance"}

    def consume_combo_override(self, name, skill, current_time):
        if self.perfect_balance_stacks > 0 and self.perfect_balance_until > current_time:
            self.perfect_balance_stacks -= 1
            self.pb_consumed += 1
            if self.pb_consumed >= 3:
                self.blitz_ready = True
            return True
        return False

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        perfect_balance_active = self.perfect_balance_stacks > 0 and self.perfect_balance_until > snapshot_time
        if canonical in {"Twin Snakes", "Rising Raptor", "Four-point Fury"}:
            if not perfect_balance_active and (self.form != "raptor" or self.form_until <= snapshot_time):
                self.warn("mnk_form_mismatch", current_time, name,
                          f"{canonical} used without tracked Raptor Form or Perfect Balance.")
        elif canonical in {"Demolish", "Pouncing Coeurl", "Snap Punch", "Rockbreaker"}:
            if not perfect_balance_active and (self.form != "coeurl" or self.form_until <= snapshot_time):
                self.warn("mnk_form_mismatch", current_time, name,
                          f"{canonical} used without tracked Coeurl Form or Perfect Balance.")
        if canonical in {"The Forbidden Chakra", "Enlightenment"} and self.chakra < 5:
            self.warn("mnk_chakra_low", current_time, name,
                      f"{canonical} used with Chakra {self.chakra}; expected 5.")
        if canonical in {"Elixir Field", "Flint Strike", "Rising Phoenix", "Phantom Rush", "Masterful Blitz"}:
            if not self.blitz_ready and not perfect_balance_active:
                self.warn("mnk_blitz_not_ready", current_time, name,
                          f"{canonical} used without a tracked completed Perfect Balance sequence.")
        return {}

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Perfect Balance":
            self.perfect_balance_stacks = 3
            self.perfect_balance_until = current_time + 20.0
            self.pb_consumed = 0
        elif canonical == "Riddle of Fire":
            self.riddle_fire_until = current_time + 20.72
        elif canonical == "Brotherhood":
            self.brotherhood_until = current_time + 20.0
            self.chakra = 5
        elif canonical == "Riddle of Wind":
            self.riddle_wind_until = current_time + 15.78
        elif canonical in {"Dragon Kick", "Leaping Opo", "Bootshine", "Shadow of the Destroyer"}:
            self.form = "raptor"
            self.form_until = current_time + 30.0
        elif canonical in {"Twin Snakes", "Rising Raptor", "Four-point Fury"}:
            self.form = "coeurl"
            self.form_until = current_time + 30.0
        elif canonical in {"Demolish", "Pouncing Coeurl", "Snap Punch", "Rockbreaker"}:
            self.form = "opo"
            self.form_until = current_time + 30.0
        elif canonical in {"The Forbidden Chakra", "Enlightenment"}:
            self.chakra = max(0, self.chakra - 5)
        elif canonical in {"Elixir Field", "Flint Strike", "Rising Phoenix", "Phantom Rush", "Masterful Blitz"}:
            self.blitz_ready = False

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        if self.riddle_fire_until > t:
            damage_mult *= 1.15
        if self.brotherhood_until > t:
            damage_mult *= 1.05
        return {
            "mnk_riddle_fire": self.riddle_fire_until > t,
            "mnk_brotherhood": self.brotherhood_until > t,
            "mnk_riddle_wind": self.riddle_wind_until > t,
            "mnk_form": self.form if self.form_until > t else None,
            "damage_mult": damage_mult,
        }

    def auto_attack_interval_multiplier(self, t):
        return 0.5 if self.riddle_wind_until > t else 1.0

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("mnk_riddle_fire"):
            labels.append("红莲")
        if active_buffs.get("mnk_brotherhood"):
            labels.append("义结")
        if active_buffs.get("mnk_riddle_wind"):
            labels.append("疾风")
        if active_buffs.get("mnk_form"):
            labels.append("身形")
        if has_potion:
            labels.append("药")
        return labels
