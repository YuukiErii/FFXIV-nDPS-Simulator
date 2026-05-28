try:
    from .base import JobState
except ImportError:
    from base import JobState


class VprJobState(JobState):
    def __init__(self):
        super().__init__("VPR")
        self.hunters_instinct_until = -1.0
        self.swiftscaled_until = -1.0
        self.reawaken_until = -1.0
        self.reawaken_stacks = 0
        self.serpent_offering = 0
        self.rattling_coils = 0
        self.twinfang_ready = False
        self.twinblood_ready = False

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {
            "Hunter's Sting", "Hunter's Coil", "Hunter's Den",
            "Swiftskin's Sting", "Swiftskin's Coil", "Swiftskin's Den",
        }

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        if canonical == "Reawaken" and self.serpent_offering < 50:
            self.warn("vpr_serpent_offering_low", current_time, name,
                      f"Reawaken used with Serpent Offering {self.serpent_offering}; expected at least 50.")
        if canonical in {"First Generation", "Second Generation", "Third Generation", "Fourth Generation"}:
            if self.reawaken_until <= snapshot_time or self.reawaken_stacks <= 0:
                self.warn("vpr_reawaken_inactive", current_time, name,
                          f"{canonical} used without a tracked Reawaken stack.")
        if canonical == "Uncoiled Fury" and self.rattling_coils <= 0:
            self.warn("vpr_rattling_coil_low", current_time, name,
                      "Uncoiled Fury used without a tracked Rattling Coil.")
        if canonical == "Twinfang" and not self.twinfang_ready:
            self.warn("vpr_twinfang_not_ready", current_time, name,
                      "Twinfang used without a tracked preceding dualblade action.")
        if canonical == "Twinblood" and not self.twinblood_ready:
            self.warn("vpr_twinblood_not_ready", current_time, name,
                      "Twinblood used without a tracked preceding dualblade action.")
        return {}

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical in {"Hunter's Sting", "Hunter's Coil", "Hunter's Den"}:
            self.hunters_instinct_until = current_time + 40.0
        elif canonical in {"Swiftskin's Sting", "Swiftskin's Coil", "Swiftskin's Den"}:
            self.swiftscaled_until = current_time + 40.0
        elif canonical == "Reawaken":
            self.serpent_offering = max(0, self.serpent_offering - 50)
            self.reawaken_until = current_time + 30.0
            self.reawaken_stacks = 5
        elif canonical in {"First Generation", "Second Generation", "Third Generation", "Fourth Generation"}:
            self.reawaken_stacks = max(0, self.reawaken_stacks - 1)
            self.twinfang_ready = True
            self.twinblood_ready = True
        elif canonical in {"Steel Fangs", "Dread Fangs", "Hunter's Sting", "Swiftskin's Sting",
                           "Hunter's Coil", "Swiftskin's Coil", "Hunter's Den", "Swiftskin's Den"}:
            self.serpent_offering = min(100, self.serpent_offering + 10)
        elif canonical in {"Serpent's Ire"}:
            self.serpent_offering = min(100, self.serpent_offering + 50)
        elif canonical in {"Vicewinder", "Vicepit"}:
            self.rattling_coils = min(3, self.rattling_coils + 1)
            self.twinfang_ready = True
            self.twinblood_ready = True
        elif canonical == "Uncoiled Fury":
            self.rattling_coils = max(0, self.rattling_coils - 1)
            self.twinfang_ready = True
            self.twinblood_ready = True
        elif canonical == "Twinfang":
            self.twinfang_ready = False
        elif canonical == "Twinblood":
            self.twinblood_ready = False

    def active_damage_buffs(self, t, target_id=None):
        return {
            "vpr_hunters": self.hunters_instinct_until > t,
            "vpr_swift": self.swiftscaled_until > t,
            "vpr_reawaken": self.reawaken_until > t and self.reawaken_stacks > 0,
            "damage_mult": 1.10 if self.hunters_instinct_until > t else 1.0,
        }

    def auto_attack_interval_multiplier(self, t):
        return 0.85 if self.swiftscaled_until > t else 1.0

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("vpr_hunters"):
            labels.append("猎手")
        if active_buffs.get("vpr_swift"):
            labels.append("迅鳞")
        if active_buffs.get("vpr_reawaken"):
            labels.append("祖灵")
        if has_potion:
            labels.append("药")
        return labels
