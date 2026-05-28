try:
    from .base import JobState
except ImportError:
    from base import JobState


class MchJobState(JobState):
    REASSEMBLE_ALLOWLIST = {
        "Heated Split Shot", "Heated Slug Shot", "Heated Clean Shot",
        "Drill", "Air Anchor", "Chain Saw", "Excavator", "Bioblaster",
        "Scattergun", "Auto Crossbow", "Blazing Shot", "Full Metal Field",
    }
    WILDFIRE_WEAPONSKILLS = REASSEMBLE_ALLOWLIST | {"Heat Blast"}
    QUEEN_FOLLOWUPS = (
        ("Armpunch", 160, 5.5),
        ("Armpunch", 160, 7.06),
        ("Armpunch", 160, 8.62),
        ("Armpunch", 160, 10.18),
        ("Armpunch", 160, 11.74),
        ("Pilebunker", 480, 13.3),
        ("Crowned Collider", 550, 15.3),
    )

    def __init__(self):
        super().__init__("MCH")
        self.reassemble_until = -1.0
        self.reassemble_ready = False
        self.overheated_until = -1.0
        self.wildfire_until = -1.0
        self.wildfire_hits = 0
        self.queen_ready_until = -1.0
        self._pending_canonical = None
        self.heat = 0
        self.battery = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Reassemble", "Hypercharge"}

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._pending_canonical = canonical
        out = {}
        if canonical == "Hypercharge" and self.heat < 50:
            self.warn("mch_heat_low", current_time, name,
                      f"Hypercharge used with Heat Gauge {self.heat}; expected at least 50.")
        elif canonical == "Heat Blast" and self.overheated_until <= snapshot_time:
            self.warn("mch_heat_blast_no_overheat", current_time, name,
                      "Heat Blast used outside Overheated window.")
        elif canonical in {"Automaton Queen", "Queen Overdrive"} and self.battery < 50:
            self.warn("mch_battery_low", current_time, name,
                      f"Automaton Queen used with Battery Gauge {self.battery}; expected at least 50.")
        elif canonical == "Detonator" and self.wildfire_until <= snapshot_time:
            self.warn("mch_detonator_without_wildfire", current_time, name,
                      "Detonator used without an active Wildfire window.")
        if self.reassemble_ready and self.reassemble_until > snapshot_time and canonical in self.REASSEMBLE_ALLOWLIST:
            out["guaranteed_crit"] = True
            out["guaranteed_dh"] = True
            self.reassemble_ready = False
            self.reassemble_until = -1.0
        if canonical in {"Wildfire", "Detonator"}:
            out["force_no_crit"] = True
            out["force_no_dh"] = True
        return out

    def on_press_complete(self, name, current_time):
        canonical = self._pending_canonical or name
        self._pending_canonical = None
        if canonical == "Wildfire":
            self.wildfire_until = current_time + 10.0
            self.wildfire_hits = 0

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Detonator":
            return 0, False
        if canonical == "Wildfire":
            if self.wildfire_until <= 0:
                return 0, False
            return min(self.wildfire_hits, 6) * 240, False
        if canonical in {"Automaton Queen", "Queen Overdrive"}:
            return 0, False
        return super().resolve_potency(name, skill, current_time, payload)

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Reassemble":
            self.reassemble_ready = True
            self.reassemble_until = current_time + 5.0
        elif canonical == "Hypercharge":
            self.heat = max(0, self.heat - 50)
            self.overheated_until = current_time + 10.0
        elif canonical == "Wildfire":
            self.wildfire_until = -1.0
            self.wildfire_hits = 0
        elif canonical == "Barrel Stabilizer":
            self.heat = min(100, self.heat + 50)
        elif canonical == "Heated Clean Shot":
            self.heat = min(100, self.heat + 5)
            self.battery = min(100, self.battery + 10)
        elif canonical in {"Air Anchor", "Chain Saw", "Excavator"}:
            self.battery = min(100, self.battery + 20)
        elif canonical in {"Automaton Queen", "Queen Overdrive"}:
            self.battery = 0
        elif self.wildfire_until > current_time and canonical in self.WILDFIRE_WEAPONSKILLS:
            self.wildfire_hits = min(6, self.wildfire_hits + 1)

    def followup_damage_events(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical not in {"Automaton Queen", "Queen Overdrive"}:
            return []
        target_count = int(payload.get("targets", 1))
        return [
            {
                "name": followup_name,
                "potency": potency,
                "delay": delay,
                "targets": target_count,
                "damage_class": "PET",
            }
            for followup_name, potency, delay in self.QUEEN_FOLLOWUPS
        ]

    def active_damage_buffs(self, t, target_id=None):
        return {
            "mch_overheated": self.overheated_until > t,
            "mch_wildfire": self.wildfire_until > t,
            "damage_mult": 1.0,
        }

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("mch_overheated"):
            labels.append("过热")
        if active_buffs.get("mch_wildfire"):
            labels.append("野火")
        if has_potion:
            labels.append("药")
        return labels
