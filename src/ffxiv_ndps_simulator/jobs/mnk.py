try:
    from .base import JobState
except ImportError:
    from base import JobState


class MnkJobState(JobState):
    TEAMMATE_CHAKRA_INTERVAL = 0.4
    FORM_SKILLS = {
        "Dragon Kick": "opo",
        "Leaping Opo": "opo",
        "Shadow of the Destroyer": "opo",
        "Twin Snakes": "raptor",
        "Rising Raptor": "raptor",
        "Four-point Fury": "raptor",
        "Demolish": "coeurl",
        "Pouncing Coeurl": "coeurl",
        "Rockbreaker": "coeurl",
    }
    NEXT_FORM = {"opo": "raptor", "raptor": "coeurl", "coeurl": "opo"}
    FURY_GENERATORS = {
        "Dragon Kick": ("opo", 1),
        "Twin Snakes": ("raptor", 1),
        "Demolish": ("coeurl", 2),
    }
    FURY_SPENDERS = {
        "Leaping Opo": ("opo", 460),
        "Rising Raptor": ("raptor", 540),
        "Pouncing Coeurl": ("coeurl", 520),
    }
    BLITZES = {
        "Elixir Field", "Elixir Burst", "Celestial Revolution",
        "Flint Strike", "Rising Phoenix", "Tornado Kick", "Phantom Rush",
        "Masterful Blitz",
    }
    WEAPONSKILLS = set(FORM_SKILLS) | BLITZES | {
        "Wind's Reply", "Fire's Reply", "Six-sided Star",
    }
    MEDITATIONS = {
        "Steeled Meditation", "Inspirited Meditation", "Forbidden Meditation",
        "Enlightened Meditation", "Meditation",
    }
    UPGRADE_NAMES = {
        "Bootshine": "Leaping Opo",
        "True Strike": "Rising Raptor",
        "Snap Punch": "Pouncing Coeurl",
        "Arm of the Destroyer": "Shadow of the Destroyer",
        "Elixir Field": "Elixir Burst",
        "Flint Strike": "Rising Phoenix",
        "Tornado Kick": "Phantom Rush",
    }
    BLITZ_POTENCY = {
        "Elixir Burst": 900,
        "Celestial Revolution": 600,
        "Rising Phoenix": 900,
        "Phantom Rush": 1500,
    }

    def __init__(self):
        super().__init__("MNK")
        self.form = None
        self.form_until = -1.0
        self.formless_until = -1.0
        self.perfect_balance_stacks = 0
        self.perfect_balance_until = -1.0
        self.beast_chakra = []
        self.lunar_nadi = False
        self.solar_nadi = False
        self.blitz_ready = False
        self.riddle_fire_until = -1.0
        self.fire_rumination_until = -1.0
        self.brotherhood_start = -1.0
        self.brotherhood_until = -1.0
        self.riddle_wind_until = -1.0
        self.wind_rumination_until = -1.0
        self.chakra = 0
        self.teammate_chakra_started_at = None
        self.teammate_chakra_applied = 0
        self.fury = {"opo": 0, "raptor": 0, "coeurl": 0}
        self.in_combat = False

    def _canonical(self, name, skill=None):
        if name == "Masterful Blitz":
            return name
        canonical = (skill or {}).get("amas_name") or name
        return self.UPGRADE_NAMES.get(canonical, canonical)

    def _form_bonus(self, canonical, current_time, payload=None):
        required = self.FORM_SKILLS.get(canonical)
        if not required:
            return False
        return bool(
            (payload or {}).get("meikyo")
            or (self.form == required and self._active_until(self.form_until, current_time))
        )

    def _expected_blitz(self):
        if len(self.beast_chakra) != 3:
            return None
        if self.lunar_nadi and self.solar_nadi:
            return "Phantom Rush"
        distinct = len(set(self.beast_chakra))
        if distinct == 1:
            return "Elixir Burst"
        if distinct == 2:
            return "Celestial Revolution"
        return "Rising Phoenix"

    def _gain_chakra(self, amount, current_time, cap=None):
        cap = cap if cap is not None else (10 if self._brotherhood_active(current_time) else 5)
        if self.chakra < cap:
            self.chakra = min(cap, self.chakra + max(0, int(amount)))

    def _brotherhood_active(self, current_time):
        return self._active_window(self.brotherhood_start, self.brotherhood_until, current_time)

    def _sync_teammate_chakra(self, current_time):
        if self.teammate_chakra_started_at is None:
            return
        end_time = min(current_time, self.brotherhood_until)
        if end_time <= self.teammate_chakra_started_at:
            return
        # ponytail: averaged party feed; replace with teammate action timeline if Task M grows one.
        available = int((end_time - self.teammate_chakra_started_at + 1e-9) // self.TEAMMATE_CHAKRA_INTERVAL)
        gained = available - self.teammate_chakra_applied
        if gained > 0:
            self._gain_chakra(gained, end_time, cap=10)
            self.teammate_chakra_applied = available
        if current_time >= self.brotherhood_until:
            self.teammate_chakra_started_at = None

    def handles_skill_buff(self, name, skill):
        canonical = self._canonical(name, skill)
        return canonical in (
            set(self.FORM_SKILLS)
            | self.BLITZES
            | {"Riddle of Fire", "Brotherhood", "Riddle of Wind", "Perfect Balance",
               "Form Shift", "Fire's Reply"}
        )

    def consume_combo_override(self, name, skill, current_time):
        canonical = self._canonical(name, skill)
        if canonical not in self.FORM_SKILLS:
            return False

        perfect_balance = (
            self.perfect_balance_stacks > 0
            and self._active_until(self.perfect_balance_until, current_time)
        )
        formless = self._active_until(self.formless_until, current_time)
        if perfect_balance:
            self.perfect_balance_stacks -= 1
            self.beast_chakra.append(self.FORM_SKILLS[canonical])
            self.blitz_ready = len(self.beast_chakra) == 3
        if formless:
            self.formless_until = -1.0
        return perfect_balance or formless

    def on_press(self, name, skill, current_time, snapshot_time):
        self._sync_teammate_chakra(current_time)
        canonical = self._canonical(name, skill)
        required_form = self.FORM_SKILLS.get(canonical)
        perfect_balance = (
            self.perfect_balance_stacks > 0
            and self._active_until(self.perfect_balance_until, snapshot_time)
        )
        formless = self._active_until(self.formless_until, snapshot_time)

        if required_form in {"raptor", "coeurl"}:
            natural_form = self.form == required_form and self._active_until(self.form_until, snapshot_time)
            if not (natural_form or perfect_balance or formless):
                self.warn(
                    "mnk_form_mismatch",
                    current_time,
                    name,
                    f"{canonical} used without tracked {required_form.title()} Form, "
                    "Perfect Balance, or Formless Fist.",
                )

        if canonical in {"The Forbidden Chakra", "Enlightenment"}:
            if self.chakra < 5 and not self._brotherhood_active(snapshot_time):
                self.warn(
                    "mnk_chakra_low",
                    current_time,
                    name,
                    f"{canonical} used with Chakra {self.chakra}; expected 5.",
                )

        if canonical in self.BLITZES:
            expected = self._expected_blitz()
            if expected is None:
                self.warn(
                    "mnk_blitz_not_ready",
                    current_time,
                    name,
                    f"{canonical} used without three tracked Beast Chakra.",
                )
            elif canonical != "Masterful Blitz" and canonical != expected:
                self.warn(
                    "mnk_blitz_mismatch",
                    current_time,
                    name,
                    f"{canonical} used while tracked Beast Chakra resolve to {expected}.",
                )

        if canonical == "Wind's Reply" and not self._active_until(self.wind_rumination_until, snapshot_time):
            self.warn(
                "mnk_wind_reply_not_ready",
                current_time,
                name,
                "Wind's Reply used without tracked Wind's Rumination.",
            )
        if canonical == "Fire's Reply" and not self._active_until(self.fire_rumination_until, snapshot_time):
            self.warn(
                "mnk_fire_reply_not_ready",
                current_time,
                name,
                "Fire's Reply used without tracked Fire's Rumination.",
            )

        out = {}
        if canonical == "Six-sided Star":
            out["mnk_chakra"] = self.chakra
        if canonical == "Masterful Blitz":
            out["mnk_blitz"] = self._expected_blitz()
        return out

    def on_press_confirmed(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Riddle of Fire":
            duration = (skill.get("buff") or {}).get("duration", 20.72)
            self.riddle_fire_until = current_time + duration
            self.fire_rumination_until = current_time + duration
        elif canonical == "Brotherhood":
            self.brotherhood_start, self.brotherhood_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
            self.teammate_chakra_started_at = self.brotherhood_start
            self.teammate_chakra_applied = 0
        elif canonical == "Riddle of Wind":
            duration = (skill.get("buff") or {}).get("duration", 15.78)
            self.riddle_wind_until = current_time + duration
            self.wind_rumination_until = current_time + duration

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        potency = skill.get("potency", 0)

        if canonical == "Masterful Blitz":
            resolved = payload.get("mnk_blitz") or self._expected_blitz()
            potency = self.BLITZ_POTENCY.get(resolved, 0)
            skill["is_aoe"] = bool(resolved and resolved != "Celestial Revolution")
            skill["decay"] = 0.35 if skill["is_aoe"] else 0.0
        elif canonical in self.BLITZ_POTENCY:
            potency = self.BLITZ_POTENCY[canonical]
        elif canonical in self.FURY_SPENDERS:
            fury, fury_potency = self.FURY_SPENDERS[canonical]
            if self.fury[fury] > 0:
                potency = fury_potency
        elif canonical == "Six-sided Star":
            potency = 780 + 80 * int(payload.get("mnk_chakra", self.chakra))

        if canonical in {"Leaping Opo", "Shadow of the Destroyer"}:
            payload["guaranteed_crit"] = self._form_bonus(canonical, current_time, payload)
        return potency, False

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        self._sync_teammate_chakra(current_time)
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if payload.get("press_time") is not None and canonical in {"Riddle of Fire", "Brotherhood", "Riddle of Wind"}:
            return

        if canonical == "Perfect Balance":
            self.perfect_balance_stacks = 3
            self.perfect_balance_until = current_time + 20.0
            self.beast_chakra = []
            self.blitz_ready = False
        elif canonical == "Form Shift":
            self.formless_until = current_time + 30.0
        elif canonical in self.MEDITATIONS:
            self._gain_chakra(1 if self.in_combat else 5, current_time)
        elif canonical == "Riddle of Fire":
            duration = (skill.get("buff") or {}).get("duration", 20.0)
            self.riddle_fire_until = current_time + duration
            self.fire_rumination_until = current_time + duration
        elif canonical == "Brotherhood":
            self.brotherhood_start, self.brotherhood_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
            self.teammate_chakra_started_at = self.brotherhood_start
            self.teammate_chakra_applied = 0
        elif canonical == "Riddle of Wind":
            duration = (skill.get("buff") or {}).get("duration", 15.0)
            self.riddle_wind_until = current_time + duration
            self.wind_rumination_until = current_time + duration
        elif canonical == "Wind's Reply":
            self.wind_rumination_until = -1.0
        elif canonical == "Fire's Reply":
            self.fire_rumination_until = -1.0
            self.formless_until = current_time + 30.0

        if canonical in self.FORM_SKILLS:
            form_bonus = self._form_bonus(canonical, current_time, payload)
            if canonical in self.FURY_GENERATORS and form_bonus:
                fury, stacks = self.FURY_GENERATORS[canonical]
                self.fury[fury] = stacks
            if canonical in self.FURY_SPENDERS:
                fury, _ = self.FURY_SPENDERS[canonical]
                if self.fury[fury] > 0:
                    self.fury[fury] -= 1
            required = self.FORM_SKILLS[canonical]
            self.form = self.NEXT_FORM[required]
            self.form_until = current_time + 30.0

        resolved_blitz = (
            payload.get("mnk_blitz")
            if canonical == "Masterful Blitz"
            else canonical
        )
        if canonical in self.BLITZES and resolved_blitz in self.BLITZ_POTENCY:
            if resolved_blitz == "Elixir Burst":
                self.lunar_nadi = True
            elif resolved_blitz == "Celestial Revolution":
                if self.lunar_nadi:
                    self.solar_nadi = True
                else:
                    self.lunar_nadi = True
            elif resolved_blitz == "Rising Phoenix":
                self.solar_nadi = True
            elif resolved_blitz == "Phantom Rush":
                self.lunar_nadi = False
                self.solar_nadi = False
            self.beast_chakra = []
            self.blitz_ready = False
            self.perfect_balance_stacks = 0
            self.formless_until = current_time + 30.0

        if canonical in {"The Forbidden Chakra", "Enlightenment"}:
            self.chakra = max(0, self.chakra - 5)
        elif canonical == "Six-sided Star":
            self.chakra = 0

        landed = bool(payload.get("source_roll_available"))
        if landed:
            self.in_combat = True
        if landed and canonical in self.WEAPONSKILLS:
            if self._brotherhood_active(current_time):
                self._gain_chakra(1, current_time)
            if canonical != "Six-sided Star":
                self._gain_chakra(payload.get("source_crit_count", int(bool(payload.get("source_crit")))), current_time)

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        damage_factors = []
        riddle_fire = self._active_until(self.riddle_fire_until, t)
        brotherhood = self._brotherhood_active(t)
        riddle_wind = self._active_until(self.riddle_wind_until, t)
        form_active = self._active_until(self.form_until, t)
        formless = self._active_until(self.formless_until, t)
        if riddle_fire:
            damage_mult *= 1.15
            damage_factors.append(("红莲", 1.15))
        if brotherhood:
            damage_mult *= 1.05
            damage_factors.append(("义结", 1.05))
        return {
            "mnk_riddle_fire": riddle_fire,
            "mnk_brotherhood": brotherhood,
            "mnk_riddle_wind": riddle_wind,
            "mnk_form": self.form if form_active else None,
            "mnk_formless": formless,
            "damage_mult": damage_mult,
            "damage_factors": damage_factors,
        }

    def auto_attack_interval_multiplier(self, t):
        return 0.4 if self._active_until(self.riddle_wind_until, t) else 0.8

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("mnk_riddle_fire"):
            labels.append("红莲")
        if active_buffs.get("mnk_brotherhood"):
            labels.append("义结")
        if active_buffs.get("mnk_riddle_wind"):
            labels.append("疾风")
        if active_buffs.get("mnk_formless"):
            labels.append("无相")
        elif active_buffs.get("mnk_form"):
            labels.append("身形")
        if has_potion:
            labels.append("药")
        return labels
