try:
    from .base import JobState
except ImportError:
    from base import JobState


class MchJobState(JobState):
    REASSEMBLE_ALLOWLIST = {
        "Split Shot", "Slug Shot", "Clean Shot", "Hot Shot",
        "Heated Split Shot", "Heated Slug Shot", "Heated Clean Shot",
        "Drill", "Air Anchor", "Chain Saw", "Excavator", "Bioblaster",
        "Scattergun", "Auto Crossbow", "Heat Blast", "Blazing Shot",
    }
    WILDFIRE_WEAPONSKILLS = REASSEMBLE_ALLOWLIST | {"Full Metal Field"}
    OVERHEAT_CONSUMERS = {"Heat Blast", "Blazing Shot", "Auto Crossbow"}
    OVERHEAT_BONUS_WEAPONSKILLS = {
        "Split Shot", "Slug Shot", "Clean Shot", "Hot Shot",
        "Heated Split Shot", "Heated Slug Shot", "Heated Clean Shot",
        "Drill", "Air Anchor", "Heat Blast", "Blazing Shot",
    }
    QUEEN_FOLLOWUPS = (
        ("Roller Dash", 240, 3.5),
        ("Armpunch", 120, 5.5),
        ("Armpunch", 120, 7.06),
        ("Armpunch", 120, 8.62),
        ("Armpunch", 120, 10.18),
        ("Armpunch", 120, 11.74),
        ("Pilebunker", 340, 13.3),
        ("Crowned Collider", 390, 15.3),
    )
    FLAMETHROWER_TICKS = tuple(float(i) for i in range(11))

    def __init__(self):
        super().__init__("MCH")
        self.reassemble_until = -1.0
        self.reassemble_ready = False
        self.overheated_until = -1.0
        self.overheated_stacks = 0
        self.hypercharged_until = -1.0
        self.wildfire_until = -1.0
        self.wildfire_hits = 0
        self.excavator_ready_until = -1.0
        self.full_metal_ready_until = -1.0
        self.flamethrower_until = -1.0
        self.flamethrower_channel_id = 0
        self._pending_wildfire_detonation = None
        self._pending_canonical = None
        self.heat = 0
        self.battery = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Reassemble", "Hypercharge"}

    @staticmethod
    def _active(until, current_time):
        return until > current_time

    def _has_overheat(self, current_time):
        if not self._active(self.overheated_until, current_time):
            self.overheated_stacks = 0
        return self.overheated_stacks > 0

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._pending_canonical = canonical
        out = {}
        overheated = self._has_overheat(snapshot_time)
        if canonical != "Flamethrower" and self._active(self.flamethrower_until, snapshot_time):
            self.flamethrower_until = snapshot_time
        if canonical == "Hypercharge" and self.heat < 50 and not self._active(self.hypercharged_until, snapshot_time):
            self.warn("mch_heat_low", current_time, name,
                      f"Hypercharge used with Heat Gauge {self.heat} and no Hypercharged state; expected at least 50 Heat or Hypercharged.")
        elif canonical in self.OVERHEAT_CONSUMERS and not overheated:
            self.warn("mch_heat_blast_no_overheat", current_time, name,
                      f"{canonical} used outside Overheated stacks.")
        elif canonical == "Excavator" and not self._active(self.excavator_ready_until, snapshot_time):
            self.warn("mch_excavator_not_ready", current_time, name,
                      "Excavator used without tracked Excavator Ready.")
        elif canonical == "Full Metal Field" and not self._active(self.full_metal_ready_until, snapshot_time):
            self.warn("mch_full_metal_not_ready", current_time, name,
                      "Full Metal Field used without tracked Full Metal Machinist.")
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
        if overheated:
            out["mch_overheated"] = True
        if canonical in {"Automaton Queen", "Queen Overdrive"}:
            out["mch_queen_battery"] = self.battery
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
        if canonical == "Flamethrower":
            return 0, False
        if canonical == "Wildfire":
            if self.wildfire_until <= 0:
                return 0, False
            return min(self.wildfire_hits, 6) * 240, False
        if canonical in {"Automaton Queen", "Queen Overdrive"}:
            return 0, False
        potency, is_combo = super().resolve_potency(name, skill, current_time, payload)
        if payload.get("mch_overheated") and canonical in self.OVERHEAT_BONUS_WEAPONSKILLS:
            potency += 20
        return potency, is_combo

    def should_resolve_damage(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Wildfire":
            return self.wildfire_until >= current_time - 1e-9
        return True

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Reassemble":
            self.reassemble_ready = True
            self.reassemble_until = current_time + 5.0
        elif canonical == "Hypercharge":
            if self._active(self.hypercharged_until, current_time):
                self.hypercharged_until = -1.0
            else:
                self.heat = max(0, self.heat - 50)
            self.overheated_until = current_time + 10.0
            self.overheated_stacks = 5
        elif canonical == "Wildfire":
            self.wildfire_until = -1.0
            self.wildfire_hits = 0
        elif canonical == "Detonator":
            if self.wildfire_until > current_time:
                self._pending_wildfire_detonation = min(self.wildfire_hits, 6) * 240
                self.wildfire_until = -1.0
                self.wildfire_hits = 0
        elif canonical == "Barrel Stabilizer":
            self.hypercharged_until = current_time + 30.0
            self.full_metal_ready_until = current_time + 30.0
        elif canonical in {"Split Shot", "Heated Split Shot"}:
            self.heat = min(100, self.heat + 5)
        elif canonical in {"Slug Shot", "Heated Slug Shot"} and is_combo:
            self.heat = min(100, self.heat + 5)
        elif canonical in {"Clean Shot", "Heated Clean Shot"} and is_combo:
            self.heat = min(100, self.heat + 5)
            self.battery = min(100, self.battery + 10)
        elif canonical == "Scattergun":
            self.heat = min(100, self.heat + 10)
        elif canonical in {"Hot Shot", "Air Anchor"}:
            self.battery = min(100, self.battery + 20)
        elif canonical == "Chain Saw":
            self.battery = min(100, self.battery + 20)
            self.excavator_ready_until = current_time + 30.0
        elif canonical == "Excavator":
            self.battery = min(100, self.battery + 20)
            self.excavator_ready_until = -1.0
        elif canonical == "Full Metal Field":
            self.full_metal_ready_until = -1.0
        elif canonical == "Flamethrower":
            self.flamethrower_channel_id += 1
            self.flamethrower_until = current_time + 10.0
        elif canonical in self.OVERHEAT_CONSUMERS and payload.get("mch_overheated"):
            self.overheated_stacks = max(0, self.overheated_stacks - 1)
            if self.overheated_stacks == 0:
                self.overheated_until = -1.0
        elif canonical in {"Automaton Queen", "Queen Overdrive"}:
            self.battery = 0

        if self.wildfire_until > current_time and canonical in self.WILDFIRE_WEAPONSKILLS:
            self.wildfire_hits = min(6, self.wildfire_hits + 1)

    @staticmethod
    def _queen_potency(base_potency, battery):
        battery = max(50, min(100, int(battery or 0)))
        return int(round(base_potency * battery / 50.0))

    def followup_damage_events(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Detonator" and self._pending_wildfire_detonation is not None:
            potency = self._pending_wildfire_detonation
            self._pending_wildfire_detonation = None
            if potency <= 0:
                return []
            return [{
                "name": "Wildfire",
                "potency": potency,
                "delay": 0.0,
                "targets": int(payload.get("targets", 1)),
                "force_no_crit": True,
                "force_no_dh": True,
                "extends_duration": False,
            }]
        if canonical == "Flamethrower":
            target_count = int(payload.get("targets", 1))
            return [
                {
                    "name": "Flamethrower",
                    "potency": 120,
                    "delay": delay,
                    "targets": target_count,
                    "is_aoe": target_count > 1,
                    "is_dot": True,
                    "mch_channel": "Flamethrower",
                    "mch_channel_id": self.flamethrower_channel_id,
                }
                for delay in self.FLAMETHROWER_TICKS
            ]
        if canonical not in {"Automaton Queen", "Queen Overdrive"}:
            return []
        target_count = int(payload.get("targets", 1))
        battery = payload.get("mch_queen_battery", self.battery)
        return [
            {
                "name": followup_name,
                "potency": self._queen_potency(potency, battery),
                "delay": delay,
                "targets": target_count,
                "damage_class": "PET",
            }
            for followup_name, potency, delay in self.QUEEN_FOLLOWUPS
        ]

    def is_followup_active(self, payload, current_time):
        if payload.get("mch_channel") != "Flamethrower":
            return True
        return (
            payload.get("mch_channel_id") == self.flamethrower_channel_id
            and current_time <= self.flamethrower_until + 1e-9
        )

    def allows_auto_attack_at(self, current_time):
        return not self._active(self.flamethrower_until, current_time)

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
