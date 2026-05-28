from collections import defaultdict

try:
    from .base import JobState
except ImportError:
    from base import JobState


class RprJobState(JobState):
    DEATHS_DESIGN_SKILLS = {"Shadow of Death", "Whorl of Death"}

    def __init__(self):
        super().__init__("RPR")
        self.deaths_design_until = defaultdict(lambda: -1.0)
        self.soul = 0
        self.shroud = 0
        self.enshroud_stacks = 0
        self.enshroud_until = -1.0
        self.soulsow_ready = False

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        if canonical in {"Blood Stalk", "Grim Swathe", "Gluttony"} and self.soul < 50:
            self.warn("rpr_soul_low", current_time, name,
                      f"{canonical} used with Soul Gauge {self.soul}; expected at least 50.")
        if canonical == "Enshroud" and self.shroud < 50:
            self.warn("rpr_shroud_low", current_time, name,
                      f"Enshroud used with Shroud Gauge {self.shroud}; expected at least 50.")
        if canonical in {"Void Reaping", "Cross Reaping", "Grim Reaping", "Lemure's Slice",
                         "Lemure's Scythe", "Communio"} and (
                self.enshroud_stacks <= 0 or self.enshroud_until <= snapshot_time):
            self.warn("rpr_enshroud_inactive", current_time, name,
                      f"{canonical} used without a tracked Enshroud stack.")
        if canonical == "Harvest Moon" and not self.soulsow_ready:
            self.warn("rpr_soulsow_missing", current_time, name,
                      "Harvest Moon used without a tracked Soulsow preparation.")
        return {}

    def _refresh_deaths_design(self, target_id, current_time):
        current_remaining = max(0.0, self.deaths_design_until[target_id] - current_time)
        self.deaths_design_until[target_id] = current_time + min(60.0, current_remaining + 30.0)

    def active_damage_buffs(self, t, target_id=None):
        target_id = target_id or 1
        is_deaths_design = self.deaths_design_until[target_id] > t
        return {
            "rpr_deaths_design": is_deaths_design,
            "damage_mult": 1.10 if is_deaths_design else 1.0,
        }

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical in self.DEATHS_DESIGN_SKILLS:
            self._refresh_deaths_design(payload.get("tid", 1), current_time)
        if canonical in {"Soul Slice", "Soul Scythe"}:
            self.soul = min(100, self.soul + 50)
        elif canonical in {"Infernal Slice", "Nightmare Scythe"} and is_combo:
            self.soul = min(100, self.soul + 10)
        elif canonical in {"Blood Stalk", "Grim Swathe", "Gluttony"}:
            self.soul = max(0, self.soul - 50)
            self.shroud = min(100, self.shroud + (50 if canonical == "Gluttony" else 10))
        elif canonical in {"Gibbet", "Gallows", "Guillotine"}:
            self.shroud = min(100, self.shroud + 10)
        elif canonical == "Enshroud":
            self.shroud = max(0, self.shroud - 50)
            self.enshroud_stacks = 5
            self.enshroud_until = current_time + 30.0
        elif canonical in {"Void Reaping", "Cross Reaping", "Grim Reaping", "Lemure's Slice",
                           "Lemure's Scythe"}:
            self.enshroud_stacks = max(0, self.enshroud_stacks - 1)
        elif canonical == "Communio":
            self.enshroud_stacks = 0
            self.enshroud_until = -1.0
        elif canonical == "Soulsow":
            self.soulsow_ready = True
        elif canonical == "Harvest Moon":
            self.soulsow_ready = False

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("rpr_deaths_design"):
            labels.append("死亡烙印")
        if active_buffs.get("damage_mult", 1.0) > (1.10 if active_buffs.get("rpr_deaths_design") else 1.0):
            labels.append("增伤")
        if has_potion:
            labels.append("药")
        return labels
