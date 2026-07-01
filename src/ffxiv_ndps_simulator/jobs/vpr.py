try:
    from .base import JobState
except ImportError:
    from base import JobState


class VprJobState(JobState):
    ST_STARTERS = {"Steel Fangs", "Reaving Fangs", "Dread Fangs"}
    ST_SECONDS = {"Hunter's Sting": "hunter", "Swiftskin's Sting": "swift"}
    ST_FINISHERS = {
        "Flanksting Strike": ("hunter", "Flankstung Venom", "Hindstung Venom"),
        "Flanksbane Fang": ("hunter", "Flanksbane Venom", "Hindsbane Venom"),
        "Hindsting Strike": ("swift", "Hindstung Venom", "Flanksbane Venom"),
        "Hindsbane Fang": ("swift", "Hindsbane Venom", "Flankstung Venom"),
    }
    AOE_STARTERS = {"Steel Maw", "Reaving Maw"}
    AOE_SECONDS = {"Hunter's Bite", "Swiftskin's Bite"}
    AOE_FINISHERS = {
        "Jagged Maw": ("Grimhunter's Venom", "Grimskin's Venom"),
        "Bloodied Maw": ("Grimskin's Venom", "Grimhunter's Venom"),
    }
    POSITIONAL_SKILLS = set(ST_FINISHERS) | {"Hunter's Coil", "Swiftskin's Coil"}
    GENERATIONS = (
        "First Generation", "Second Generation", "Third Generation", "Fourth Generation",
    )
    LEGACIES = (
        "First Legacy", "Second Legacy", "Third Legacy", "Fourth Legacy",
    )
    FOLLOWUPS = {
        "Twinfang Bite": ("coil", "hunter", "swift"),
        "Twinblood Bite": ("coil", "swift", "hunter"),
        "Twinfang Thresh": ("den", "fellhunter", "fellskin"),
        "Twinblood Thresh": ("den", "fellskin", "fellhunter"),
        "Uncoiled Twinfang": ("uncoiled", "twinfang", "twinblood"),
        "Uncoiled Twinblood": ("uncoiled", "twinblood", "twinfang"),
    }
    NO_TARGET_WEAPONSKILLS = {
        "Steel Maw", "Reaving Maw", "Hunter's Bite", "Swiftskin's Bite",
        "Jagged Maw", "Bloodied Maw", "Last Lash", "Vicepit",
        "Hunter's Den", "Swiftskin's Den", "Twinfang Thresh", "Twinblood Thresh",
        "Reawaken",
    }

    def __init__(self):
        super().__init__("VPR")
        self.hunters_instinct_until = -1.0
        self.swiftscaled_until = -1.0
        self.honed = None
        self.honed_until = -1.0
        self.finisher_venom = None
        self.finisher_venom_until = -1.0
        self.st_combo = None
        self.st_combo_until = -1.0
        self.aoe_combo = None
        self.aoe_combo_until = -1.0
        self.death_rattle_ready = False
        self.last_lash_ready = False
        self.coil_ready = {"hunter": -1.0, "swift": -1.0}
        self.den_ready = {"hunter": -1.0, "swift": -1.0}
        self.followup_kind = None
        self.followup_charges = 0
        self.followup_venom = None
        self.followup_venom_until = -1.0
        self.ready_to_reawaken_until = -1.0
        self.reawaken_until = -1.0
        self.reawaken_stacks = 0
        self.reawaken_step = 0
        self.legacy_ready = 0
        self.serpent_offering = 0
        self.rattling_coils = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    @staticmethod
    def _active(until, current_time):
        return until > current_time

    def _expire(self, current_time):
        if not self._active(self.reawaken_until, current_time):
            self.reawaken_stacks = 0
            self.reawaken_step = 0
            self.legacy_ready = 0
        if not self._active(self.honed_until, current_time):
            self.honed = None
        if not self._active(self.finisher_venom_until, current_time):
            self.finisher_venom = None
        if not self._active(self.followup_venom_until, current_time):
            self.followup_venom = None
        if not self._active(self.st_combo_until, current_time):
            self.st_combo = None
        if not self._active(self.aoe_combo_until, current_time):
            self.aoe_combo = None

    def _paired_ready(self, ready, key, current_time):
        return self._active(ready[key], current_time)

    def _followup_ready(self, kind):
        return self.followup_kind == kind and self.followup_charges > 0

    def _generation_index(self, canonical):
        return self.GENERATIONS.index(canonical) + 1 if canonical in self.GENERATIONS else 0

    def _legacy_index(self, canonical):
        return self.LEGACIES.index(canonical) + 1 if canonical in self.LEGACIES else 0

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {
            "Hunter's Sting", "Hunter's Bite", "Hunter's Coil", "Hunter's Den",
            "Swiftskin's Sting", "Swiftskin's Bite", "Swiftskin's Coil", "Swiftskin's Den",
        }

    def can_activate_without_target(self, name, skill):
        return self._canonical(name, skill) in self.NO_TARGET_WEAPONSKILLS

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._expire(snapshot_time)
        press_state = {}
        reawakened = self._active(self.reawaken_until, snapshot_time) and self.reawaken_stacks > 0
        if canonical in self.POSITIONAL_SKILLS and self._event_context.get("positional_hit") is False:
            press_state["positional_hit"] = False

        if canonical in self.ST_SECONDS and self.st_combo != "starter":
            self.warn("vpr_st_combo_invalid", current_time, name,
                      f"{canonical} used without a tracked Steel/Reaving Fangs starter.")
        elif canonical in self.ST_FINISHERS and self.st_combo != self.ST_FINISHERS[canonical][0]:
            self.warn("vpr_st_combo_invalid", current_time, name,
                      f"{canonical} used without its tracked second-step combo.")
        elif canonical in self.AOE_SECONDS and self.aoe_combo != "starter":
            self.warn("vpr_aoe_combo_invalid", current_time, name,
                      f"{canonical} used without a tracked Steel/Reaving Maw starter.")
        elif canonical in self.AOE_FINISHERS and self.aoe_combo != "second":
            self.warn("vpr_aoe_combo_invalid", current_time, name,
                      f"{canonical} used without a tracked Hunter/Swiftskin's Bite step.")

        if canonical == "Reawaken" and (
                not self._active(self.ready_to_reawaken_until, snapshot_time)
                and self.serpent_offering < 50):
            self.warn("vpr_serpent_offering_low", current_time, name,
                      f"Reawaken used with Serpent Offering {self.serpent_offering} and no Ready to Reawaken.")
        generation = self._generation_index(canonical)
        if generation and (not reawakened or self.reawaken_step != generation - 1):
            self.warn("vpr_reawaken_order", current_time, name,
                      f"{canonical} used at tracked Reawaken step {self.reawaken_step} with {self.reawaken_stacks} tribute.")
        if canonical == "Ouroboros" and not reawakened:
            self.warn("vpr_reawaken_inactive", current_time, name,
                      "Ouroboros used without an active Anguine Tribute.")
        legacy = self._legacy_index(canonical)
        if legacy and self.legacy_ready != legacy:
            self.warn("vpr_legacy_not_ready", current_time, name,
                      f"{canonical} used while tracked Legacy readiness is {self.legacy_ready}.")

        if canonical == "Uncoiled Fury" and self.rattling_coils <= 0:
            self.warn("vpr_rattling_coil_low", current_time, name,
                      "Uncoiled Fury used without a tracked Rattling Coil.")
        if canonical == "Death Rattle" and not self.death_rattle_ready:
            self.warn("vpr_death_rattle_not_ready", current_time, name,
                      "Death Rattle used without a tracked combo finisher.")
        if canonical == "Last Lash" and not self.last_lash_ready:
            self.warn("vpr_last_lash_not_ready", current_time, name,
                      "Last Lash used without a tracked AoE combo finisher.")

        paired = {
            "Hunter's Coil": (self.coil_ready, "hunter"),
            "Swiftskin's Coil": (self.coil_ready, "swift"),
            "Hunter's Den": (self.den_ready, "hunter"),
            "Swiftskin's Den": (self.den_ready, "swift"),
        }.get(canonical)
        if paired:
            press_state["vpr_paired_valid"] = self._paired_ready(*paired, snapshot_time)
            if not press_state["vpr_paired_valid"]:
                self.warn("vpr_twinblade_not_ready", current_time, name,
                          f"{canonical} used without its tracked Vicewinder/Vicepit readiness.")

        followup = self.FOLLOWUPS.get(canonical)
        if followup:
            kind, venom, _ = followup
            if not self._followup_ready(kind):
                self.warn("vpr_followup_not_ready", current_time, name,
                          f"{canonical} used without a tracked {kind} follow-up charge.")
            elif self.followup_venom != venom:
                self.warn("vpr_followup_unbuffed", current_time, name,
                          f"{canonical} used without its matching venom enhancement.")
            potency, _ = self.resolve_potency(name, skill, snapshot_time, {})
            press_state["vpr_potency"] = potency
        return press_state

    def on_press_confirmed(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        self._expire(current_time)
        paired_valid = payload.get("vpr_paired_valid", {
            "Hunter's Coil": self._paired_ready(self.coil_ready, "hunter", current_time),
            "Swiftskin's Coil": self._paired_ready(self.coil_ready, "swift", current_time),
            "Hunter's Den": self._paired_ready(self.den_ready, "hunter", current_time),
            "Swiftskin's Den": self._paired_ready(self.den_ready, "swift", current_time),
        }.get(canonical, False))

        if skill.get("is_gcd"):
            self._clear_gcd_followups()
            self._consume_paired_ready(canonical, current_time)

        if canonical in self.ST_FINISHERS and self.st_combo == self.ST_FINISHERS[canonical][0]:
            self.death_rattle_ready = True
        elif canonical in self.AOE_FINISHERS and self.aoe_combo == "second":
            self.last_lash_ready = True
        elif canonical == "Uncoiled Fury" and self.rattling_coils > 0:
            self._grant_followups("uncoiled", "twinfang", current_time, 60.0)
        elif canonical in {"Hunter's Coil", "Swiftskin's Coil"} and paired_valid:
            venom = "hunter" if canonical == "Hunter's Coil" else "swift"
            self._grant_followups("coil", venom, current_time, 30.0)
            other = "swift" if venom == "hunter" else "hunter"
            if self._active(self.coil_ready[other], current_time):
                self.coil_ready[other] = current_time + 30.0
        elif canonical in {"Hunter's Den", "Swiftskin's Den"} and paired_valid:
            venom = "fellhunter" if canonical == "Hunter's Den" else "fellskin"
            self._grant_followups("den", venom, current_time, 30.0)
            other = "swift" if canonical == "Hunter's Den" else "hunter"
            if self._active(self.den_ready[other], current_time):
                self.den_ready[other] = current_time + 30.0

        generation = self._generation_index(canonical)
        if generation and self._active(self.reawaken_until, current_time) and self.reawaken_stacks > 0:
            self.legacy_ready = generation
        elif canonical in self.LEGACIES:
            self.legacy_ready = 0
        elif canonical in self.FOLLOWUPS:
            self._consume_followup(canonical, current_time)
        elif canonical == "Death Rattle":
            self.death_rattle_ready = False
        elif canonical == "Last Lash":
            self.last_lash_ready = False

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        self._expire(current_time)
        if "vpr_potency" in payload:
            return payload["vpr_potency"], False
        potency, is_combo = super().resolve_potency(name, skill, current_time, payload)

        if canonical in {"Steel Fangs", "Reaving Fangs", "Dread Fangs"}:
            enhanced = ((canonical == "Steel Fangs" and self.honed == "steel")
                        or (canonical in {"Reaving Fangs", "Dread Fangs"} and self.honed == "reavers"))
            return (300 if enhanced else 200), False
        if canonical in {"Steel Maw", "Reaving Maw"}:
            enhanced = ((canonical == "Steel Maw" and self.honed == "steel")
                        or (canonical == "Reaving Maw" and self.honed == "reavers"))
            return (140 if enhanced else 120), False
        if canonical in self.ST_FINISHERS:
            required_combo, consumes, _ = self.ST_FINISHERS[canonical]
            base = 340 if payload.get("positional_hit") is False else 400
            return base + (100 if self.finisher_venom == consumes else 0), self.st_combo == required_combo
        if canonical in self.AOE_FINISHERS:
            consumes, _ = self.AOE_FINISHERS[canonical]
            return 180 + (40 if self.finisher_venom == consumes else 0), self.aoe_combo == "second"
        if canonical in {"Hunter's Coil", "Swiftskin's Coil"}:
            return (630 if payload.get("positional_hit") is False else 680), self._paired_ready(
                self.coil_ready, "hunter" if canonical == "Hunter's Coil" else "swift", current_time)
        if canonical in self.FOLLOWUPS:
            kind, venom, _ = self.FOLLOWUPS[canonical]
            bonus = {"coil": 50, "den": 30, "uncoiled": 50}[kind]
            base = 50 if kind == "den" else 120
            return base + (bonus if self._followup_ready(kind) and self.followup_venom == venom else 0), False
        generation = self._generation_index(canonical)
        if generation:
            is_combo = (self._active(self.reawaken_until, current_time)
                        and self.reawaken_stacks > 0
                        and self.reawaken_step == generation - 1)
            return (680 if is_combo else 480), is_combo
        return potency, is_combo

    def _clear_gcd_followups(self):
        self.death_rattle_ready = False
        self.last_lash_ready = False
        self.followup_kind = None
        self.followup_charges = 0
        self.followup_venom = None
        self.followup_venom_until = -1.0
        self.legacy_ready = 0

    def _consume_paired_ready(self, canonical, current_time):
        if canonical in {"Uncoiled Fury", "Writhing Snap"}:
            return
        for ready, hunter_skill, swift_skill in (
            (self.coil_ready, "Hunter's Coil", "Swiftskin's Coil"),
            (self.den_ready, "Hunter's Den", "Swiftskin's Den"),
        ):
            if canonical == hunter_skill:
                ready["hunter"] = -1.0
            elif canonical == swift_skill:
                ready["swift"] = -1.0
            else:
                ready["hunter"] = ready["swift"] = -1.0
            for key in ready:
                if not self._active(ready[key], current_time):
                    ready[key] = -1.0

    def _grant_followups(self, kind, venom, current_time, duration):
        self.followup_kind = kind
        self.followup_charges = 2
        self.followup_venom = venom
        self.followup_venom_until = current_time + duration

    def _consume_followup(self, canonical, current_time):
        kind, consumes, applies = self.FOLLOWUPS[canonical]
        if not self._followup_ready(kind):
            return
        self.followup_charges -= 1
        if self.followup_venom == consumes:
            self.followup_venom = applies if self.followup_charges else None
            if self.followup_venom:
                self.followup_venom_until = current_time + (60.0 if kind == "uncoiled" else 30.0)
        elif self.followup_venom == applies:
            self.followup_venom = None
        if self.followup_charges <= 0:
            self.followup_kind = None

    def _gain_offering(self, amount):
        self.serpent_offering = min(100, self.serpent_offering + amount)

    def _end_reawaken(self):
        self.reawaken_until = -1.0
        self.reawaken_stacks = 0
        self.reawaken_step = 0
        self.legacy_ready = 0

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        canonical = self._canonical(name, skill)
        self._expire(current_time)
        landed = not payload.get("damage_immune", False)
        st_combo = self.st_combo
        aoe_combo = self.aoe_combo
        generation = self._generation_index(canonical)
        paired_valid = payload.get("vpr_paired_valid", {
            "Hunter's Coil": self._paired_ready(self.coil_ready, "hunter", current_time),
            "Swiftskin's Coil": self._paired_ready(self.coil_ready, "swift", current_time),
            "Hunter's Den": self._paired_ready(self.den_ready, "hunter", current_time),
            "Swiftskin's Den": self._paired_ready(self.den_ready, "swift", current_time),
        }.get(canonical, False))

        super().on_damage_resolved(name, skill, current_time, is_combo, payload)

        if canonical == "Serpent's Ire":
            self.rattling_coils = min(3, self.rattling_coils + 1)
            self.ready_to_reawaken_until = current_time + 30.0
        elif canonical == "Reawaken":
            if self._active(self.ready_to_reawaken_until, current_time):
                self.ready_to_reawaken_until = -1.0
            else:
                self.serpent_offering = max(0, self.serpent_offering - 50)
            self.reawaken_until = current_time + 30.0
            self.reawaken_stacks = 5
            self.reawaken_step = 0
        elif generation:
            if self._active(self.reawaken_until, current_time) and self.reawaken_stacks > 0:
                self.reawaken_stacks -= 1
                self.reawaken_step = generation
                if self.reawaken_stacks == 0:
                    self._end_reawaken()
        elif canonical == "Ouroboros":
            self._end_reawaken()
        elif canonical == "Uncoiled Fury":
            self.rattling_coils = max(0, self.rattling_coils - 1)

        if canonical in self.ST_STARTERS and landed:
            self.st_combo = "starter"
            self.st_combo_until = current_time + 30.0
        elif canonical in self.ST_SECONDS:
            if landed and st_combo == "starter":
                self.st_combo = self.ST_SECONDS[canonical]
                self.st_combo_until = current_time + 30.0
                if canonical == "Hunter's Sting":
                    self.hunters_instinct_until = current_time + 40.0
                else:
                    self.swiftscaled_until = current_time + 40.0
            else:
                self.st_combo = None
        elif canonical in self.ST_FINISHERS:
            required_combo, _, applies = self.ST_FINISHERS[canonical]
            if landed and st_combo == required_combo:
                self._gain_offering(10)
                self.finisher_venom = applies
                self.finisher_venom_until = current_time + 60.0
            self.st_combo = None

        if canonical in self.AOE_STARTERS and landed:
            self.aoe_combo = "starter"
            self.aoe_combo_until = current_time + 30.0
        elif canonical in self.AOE_SECONDS:
            if landed and aoe_combo == "starter":
                self.aoe_combo = "second"
                self.aoe_combo_until = current_time + 30.0
                if canonical == "Hunter's Bite":
                    self.hunters_instinct_until = current_time + 40.0
                else:
                    self.swiftscaled_until = current_time + 40.0
            else:
                self.aoe_combo = None
        elif canonical in self.AOE_FINISHERS:
            if landed and aoe_combo == "second":
                _, applies = self.AOE_FINISHERS[canonical]
                self._gain_offering(10)
                self.finisher_venom = applies
                self.finisher_venom_until = current_time + 60.0
            self.aoe_combo = None

        if canonical in {"Steel Fangs", "Steel Maw"} and landed:
            self.honed = "reavers"
            self.honed_until = current_time + 60.0
        elif canonical in {"Reaving Fangs", "Dread Fangs", "Reaving Maw"} and landed:
            self.honed = "steel"
            self.honed_until = current_time + 60.0

        if canonical == "Vicewinder":
            if landed:
                self.rattling_coils = min(3, self.rattling_coils + 1)
            self.coil_ready = {"hunter": current_time + 30.0, "swift": current_time + 30.0}
        elif canonical == "Vicepit":
            if landed:
                self.rattling_coils = min(3, self.rattling_coils + 1)
            self.den_ready = {"hunter": current_time + 30.0, "swift": current_time + 30.0}
        elif canonical in {"Hunter's Coil", "Swiftskin's Coil"} and landed and paired_valid:
            self._gain_offering(5)
            if canonical == "Hunter's Coil":
                self.hunters_instinct_until = current_time + 40.0
            else:
                self.swiftscaled_until = current_time + 40.0
        elif canonical in {"Hunter's Den", "Swiftskin's Den"} and landed and paired_valid:
            self._gain_offering(5)
            if canonical == "Hunter's Den":
                self.hunters_instinct_until = current_time + 40.0
            else:
                self.swiftscaled_until = current_time + 40.0

    def active_damage_buffs(self, t, target_id=None):
        self._expire(t)
        hunters = self._active(self.hunters_instinct_until, t)
        swift = self._active(self.swiftscaled_until, t)
        return {
            "vpr_hunters": hunters,
            "vpr_swift": swift,
            "vpr_reawaken": self._active(self.reawaken_until, t) and self.reawaken_stacks > 0,
            "damage_mult": 1.10 if hunters else 1.0,
            "damage_factors": [("猎手", 1.10)] if hunters else [],
        }

    def auto_attack_interval_multiplier(self, t):
        return 0.85 if self._active(self.swiftscaled_until, t) else 1.0

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
