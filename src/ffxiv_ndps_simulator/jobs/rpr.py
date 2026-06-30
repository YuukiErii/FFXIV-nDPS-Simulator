from collections import defaultdict

try:
    from .base import JobState
except ImportError:
    from base import JobState


class RprJobState(JobState):
    DEATHS_DESIGN_SKILLS = {"Shadow of Death", "Whorl of Death"}
    SOUL_10_GAINERS = {
        "Slice", "Spinning Scythe", "Harpe", "Harvest Moon",
    }
    SOUL_10_COMBO_GAINERS = {"Waxing Slice", "Infernal Slice", "Nightmare Scythe"}
    SOUL_50_GAINERS = {"Soul Slice", "Soul Scythe"}
    SOUL_SPENDERS = {
        "Blood Stalk", "Unveiled Gibbet", "Unveiled Gallows",
        "Grim Swathe", "Gluttony",
    }
    SOUL_REAVER_SKILLS = {"Gibbet", "Gallows", "Guillotine"}
    EXECUTIONER_SKILLS = {
        "Executioner's Gibbet", "Executioner's Gallows", "Executioner's Guillotine",
    }
    COMBO_WEAPONSKILLS = {
        "Slice", "Waxing Slice", "Infernal Slice", "Spinning Scythe", "Nightmare Scythe",
    }
    LEMURE_SKILLS = {"Void Reaping", "Cross Reaping", "Grim Reaping"}
    VOID_SPENDERS = {"Lemure's Slice", "Lemure's Scythe"}
    ENSHROUD_ALLOWED = {
        "Shadow of Death", "Whorl of Death", "Harvest Moon", "Harpe", "Soulsow",
        "Void Reaping", "Cross Reaping", "Grim Reaping", "Lemure's Slice",
        "Lemure's Scythe", "Sacrificium", "Communio", "Arcane Circle",
        "Hell's Egress", "Hell's Ingress", "Regress", "Arcane Crest",
        "Feint", "Bloodbath", "True North", "Arms Length", "Arm's Length",
        "Second Wind", "Sprint", "Tincture",
    }

    def __init__(self):
        super().__init__("RPR")
        self.deaths_design_until = defaultdict(lambda: -1.0)
        self.soul = 0
        self.shroud = 0
        self.soul_reaver = 0
        self.soul_reaver_until = -1.0
        self.executioner = 0
        self.executioner_until = -1.0
        self.enhanced_gibbet = -1.0
        self.enhanced_gallows = -1.0
        self.enshrouded_until = -1.0
        self.lemure_shroud = 0
        self.void_shroud = 0
        self.oblatio = 0
        self.enhanced_void_reaping = 0
        self.enhanced_cross_reaping = 0
        self.ideal_host = -1.0
        self.perfectio_occulta = -1.0
        self.perfectio_parata = -1.0
        self.immortal_sacrifice = 8
        self.immortal_sacrifice_until = float("inf")
        self.bloodsown_circle_until = -1.0
        self.soulsow_ready = True
        self.threshold_until = -1.0
        self.enhanced_harpe_until = -1.0
        self.crest_borrowed_until = -1.0
        self._pending_presses = {}

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    @staticmethod
    def _active(until, current_time):
        return until > current_time

    def _exit_enshroud(self):
        self.enshrouded_until = -1.0
        self.lemure_shroud = 0
        self.void_shroud = 0
        self.oblatio = 0
        self.enhanced_void_reaping = 0
        self.enhanced_cross_reaping = 0

    def _expire_timed_state(self, current_time):
        if not self._active(self.soul_reaver_until, current_time):
            self.soul_reaver = 0
        if not self._active(self.executioner_until, current_time):
            self.executioner = 0
        if self.lemure_shroud and not self._active(self.enshrouded_until, current_time):
            self._exit_enshroud()

    def _consume_lemure(self):
        self.lemure_shroud = max(0, self.lemure_shroud - 1)
        self.void_shroud = min(5, self.void_shroud + 1)
        if self.lemure_shroud == 0:
            self._exit_enshroud()

    @staticmethod
    def _affected_target_ids(payload):
        explicit = payload.get("target_ids")
        if explicit:
            return [int(target_id) for target_id in explicit]
        primary = int(payload.get("tid", 1))
        count = max(1, int(payload.get("targets", 1)))
        if count == 1:
            return [primary]
        return sorted(set(range(1, count + 1)) | {primary})

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._expire_timed_state(snapshot_time)
        enshrouded = self._active(self.enshrouded_until, snapshot_time)
        if enshrouded and canonical not in self.ENSHROUD_ALLOWED:
            self.warn("rpr_enshroud_action_blocked", current_time, name,
                      f"{canonical} used during Enshroud but is not tracked as an Enshroud action.")
        if canonical in self.SOUL_SPENDERS and self.soul < 50:
            self.warn("rpr_soul_low", current_time, name,
                      f"{canonical} used with Soul Gauge {self.soul}; expected at least 50.")
        if canonical in self.SOUL_REAVER_SKILLS and (
                self.soul_reaver <= 0 or not self._active(self.soul_reaver_until, snapshot_time)):
            self.warn("rpr_soul_reaver_missing", current_time, name,
                      f"{canonical} used without Soul Reaver.")
        if canonical in self.EXECUTIONER_SKILLS and (
                self.executioner <= 0 or not self._active(self.executioner_until, snapshot_time)):
            self.warn("rpr_executioner_missing", current_time, name,
                      f"{canonical} used without Executioner.")
        if canonical == "Enshroud" and self.shroud < 50 and not self._active(
                self.ideal_host, snapshot_time):
            self.warn("rpr_shroud_low", current_time, name,
                      f"Enshroud used with Shroud Gauge {self.shroud}; expected at least 50.")
        if canonical in self.LEMURE_SKILLS and (not enshrouded or self.lemure_shroud <= 0):
            self.warn("rpr_lemure_low", current_time, name,
                      f"{canonical} used with Lemure Shroud {self.lemure_shroud}.")
        if canonical in self.VOID_SPENDERS and (not enshrouded or self.void_shroud < 2):
            self.warn("rpr_void_low", current_time, name,
                      f"{canonical} used with Void Shroud {self.void_shroud}; expected at least 2.")
        if canonical == "Sacrificium" and (not enshrouded or self.oblatio <= 0):
            self.warn("rpr_oblatio_missing", current_time, name,
                      "Sacrificium used without Oblatio.")
        if canonical == "Communio" and not enshrouded:
            self.warn("rpr_enshroud_inactive", current_time, name,
                      "Communio used outside Enshroud.")
        if canonical == "Perfectio" and not self._active(self.perfectio_parata, snapshot_time):
            self.warn("rpr_perfectio_missing", current_time, name,
                      "Perfectio used without Perfectio Parata.")
        if canonical == "Unveiled Gibbet" and not self._active(self.enhanced_gibbet, snapshot_time):
            self.warn("rpr_enhanced_gibbet_missing", current_time, name,
                      "Unveiled Gibbet used without Enhanced Gibbet.")
        if canonical == "Unveiled Gallows" and not self._active(self.enhanced_gallows, snapshot_time):
            self.warn("rpr_enhanced_gallows_missing", current_time, name,
                      "Unveiled Gallows used without Enhanced Gallows.")
        if canonical == "Plentiful Harvest":
            if self.immortal_sacrifice <= 0 or not self._active(
                    self.immortal_sacrifice_until, snapshot_time):
                self.warn("rpr_immortal_sacrifice_missing", current_time, name,
                          "Plentiful Harvest used without Immortal Sacrifice.")
            if self._active(self.bloodsown_circle_until, snapshot_time):
                self.warn("rpr_bloodsown_circle_active", current_time, name,
                          "Plentiful Harvest used before Bloodsown Circle expired.")
        if canonical == "Harvest Moon" and not self.soulsow_ready:
            self.warn("rpr_soulsow_missing", current_time, name,
                      "Harvest Moon used without a tracked Soulsow preparation.")
        if canonical == "Regress" and not self._active(self.threshold_until, snapshot_time):
            self.warn("rpr_threshold_missing", current_time, name,
                      "Regress used without Threshold.")
        if canonical == "Pop Arcane Crest" and not self._active(self.crest_borrowed_until, snapshot_time):
            self.warn("rpr_arcane_crest_missing", current_time, name,
                      "Pop Arcane Crest used without Crest of Time Borrowed.")

        pending = {
            "canonical": canonical,
            "is_combo": self.is_combo(name, skill, current_time, {}),
            "immortal_sacrifice": (
                self.immortal_sacrifice
                if self._active(self.immortal_sacrifice_until, snapshot_time)
                else 0
            ),
            "enhanced_gibbet": self._active(self.enhanced_gibbet, snapshot_time),
            "enhanced_gallows": self._active(self.enhanced_gallows, snapshot_time),
            "enhanced_void_reaping": self.enhanced_void_reaping > 0,
            "enhanced_cross_reaping": self.enhanced_cross_reaping > 0,
        }
        self._pending_presses[(name, current_time)] = pending
        return {
            "rpr_is_combo": pending["is_combo"],
            "rpr_immortal_sacrifice_stacks": pending["immortal_sacrifice"],
            "rpr_enhanced_gibbet_applied": pending["enhanced_gibbet"],
            "rpr_enhanced_gallows_applied": pending["enhanced_gallows"],
            "rpr_enhanced_void_reaping_applied": pending["enhanced_void_reaping"],
            "rpr_enhanced_cross_reaping_applied": pending["enhanced_cross_reaping"],
        }

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

    def on_press_confirmed(self, name, skill, current_time, payload):
        pending = self._pending_presses.pop((name, current_time), None) or {
            "canonical": self._canonical(name, skill),
            "is_combo": self.is_combo(name, skill, current_time, payload),
        }
        canonical = pending["canonical"]
        is_gcd = bool(payload.get("is_gcd") if payload.get("is_gcd") is not None else skill.get("is_gcd"))

        if (canonical in self.SOUL_10_GAINERS
                or canonical in self.SOUL_10_COMBO_GAINERS and pending["is_combo"]
                or canonical == "+10 Soul Gauge"):
            self.soul = min(100, self.soul + 10)
        elif canonical in self.SOUL_50_GAINERS:
            self.soul = min(100, self.soul + 50)
        if canonical in self.SOUL_SPENDERS:
            self.soul = max(0, self.soul - 50)

        if canonical in self.SOUL_REAVER_SKILLS | self.EXECUTIONER_SKILLS:
            self.shroud = min(100, self.shroud + 10)
        if canonical == "Enshroud":
            if self._active(self.ideal_host, current_time):
                self.ideal_host = -1.0
            else:
                self.shroud = max(0, self.shroud - 50)
            self.enshrouded_until = current_time + 30.0
            self.lemure_shroud = 5
            self.void_shroud = 0
            self.oblatio = 1
            self.perfectio_parata = -1.0

        if canonical in self.SOUL_REAVER_SKILLS:
            self.soul_reaver = max(0, self.soul_reaver - 1)
            if self.soul_reaver == 0:
                self.soul_reaver_until = -1.0
        elif canonical in self.EXECUTIONER_SKILLS:
            self.executioner = max(0, self.executioner - 1)
            if self.executioner == 0:
                self.executioner_until = -1.0
        elif is_gcd:
            self.soul_reaver = 0
            self.soul_reaver_until = -1.0
            self.executioner = 0
            self.executioner_until = -1.0

        if canonical in {"Blood Stalk", "Unveiled Gibbet", "Unveiled Gallows", "Grim Swathe"}:
            self.soul_reaver = 1
            self.soul_reaver_until = current_time + 30.0
            self.executioner = 0
            self.executioner_until = -1.0
        elif canonical == "Gluttony":
            self.soul_reaver = 0
            self.soul_reaver_until = -1.0
            self.executioner = 2
            self.executioner_until = current_time + 30.0

        if canonical in {"Gibbet", "Executioner's Gibbet"}:
            self.enhanced_gibbet = -1.0
            self.enhanced_gallows = current_time + 60.0
        elif canonical in {"Gallows", "Executioner's Gallows"}:
            self.enhanced_gallows = -1.0
            self.enhanced_gibbet = current_time + 60.0

        if canonical == "Void Reaping":
            self.enhanced_void_reaping = 0
            self.enhanced_cross_reaping = 1
            self._consume_lemure()
        elif canonical == "Cross Reaping":
            self.enhanced_cross_reaping = 0
            self.enhanced_void_reaping = 1
            self._consume_lemure()
        elif canonical == "Grim Reaping":
            self._consume_lemure()
        elif canonical in self.VOID_SPENDERS:
            self.void_shroud = max(0, self.void_shroud - 2)
        elif canonical == "Sacrificium":
            self.oblatio = 0
        elif canonical == "Communio":
            if self._active(self.perfectio_occulta, current_time):
                self.perfectio_occulta = -1.0
                self.perfectio_parata = current_time + 30.0
            self._exit_enshroud()
        elif canonical == "Perfectio":
            self.perfectio_parata = -1.0

        if canonical == "Arcane Circle":
            self.immortal_sacrifice = 8
            self.immortal_sacrifice_until = current_time + 30.0
            self.bloodsown_circle_until = current_time + 6.0
        elif canonical == "Plentiful Harvest":
            self.immortal_sacrifice = 0
            self.immortal_sacrifice_until = -1.0
            self.ideal_host = current_time + 30.0
            self.perfectio_occulta = current_time + 30.0

        if canonical == "Soulsow":
            self.soulsow_ready = True
        elif canonical == "Harvest Moon":
            self.soulsow_ready = False

        if canonical in {"Hell's Ingress", "Hell's Egress"}:
            self.threshold_until = current_time + 10.0
            self.enhanced_harpe_until = current_time + 10.0
        elif canonical == "Regress":
            self.threshold_until = -1.0
        elif canonical == "Harpe":
            self.enhanced_harpe_until = -1.0
        elif canonical == "Arcane Crest":
            self.crest_borrowed_until = current_time + 5.0
        elif canonical == "Pop Arcane Crest":
            self.crest_borrowed_until = -1.0

    def effective_cast_time(self, name, skill, event, current_time, default_cast_time):
        if event.get("cast_time") is None and self._canonical(name, skill) == "Harpe" and self._active(
                self.enhanced_harpe_until, current_time):
            return 0.0
        return default_cast_time

    def resolve_potency(self, name, skill, current_time, payload):
        potency, is_combo = super().resolve_potency(name, skill, current_time, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Plentiful Harvest":
            stacks = int(payload.get("rpr_immortal_sacrifice_stacks", self.immortal_sacrifice) or 0)
            potency = 720 + max(0, stacks - 1) * 40
        elif canonical in {"Gibbet", "Executioner's Gibbet"} and payload.get("rpr_enhanced_gibbet_applied"):
            potency += 60
        elif canonical in {"Gallows", "Executioner's Gallows"} and payload.get("rpr_enhanced_gallows_applied"):
            potency += 60
        elif canonical == "Void Reaping" and payload.get("rpr_enhanced_void_reaping_applied"):
            potency += 60
        elif canonical == "Cross Reaping" and payload.get("rpr_enhanced_cross_reaping_applied"):
            potency += 60
        return potency, is_combo

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        canonical = self._canonical(name, skill)
        if canonical in self.COMBO_WEAPONSKILLS:
            super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        if payload.get("damage_immune"):
            return
        if canonical == "Shadow of Death":
            self._refresh_deaths_design(payload.get("tid", 1), current_time)
        elif canonical == "Whorl of Death":
            for target_id in self._affected_target_ids(payload):
                self._refresh_deaths_design(target_id, current_time)

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("rpr_deaths_design"):
            labels.append("死亡烙印")
        if active_buffs.get("damage_mult", 1.0) > (1.10 if active_buffs.get("rpr_deaths_design") else 1.0):
            labels.append("增伤")
        if has_potion:
            labels.append("药")
        return labels
