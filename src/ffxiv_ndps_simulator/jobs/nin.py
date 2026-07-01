from collections import defaultdict
from decimal import Decimal

try:
    from .base import JobState
except ImportError:
    from base import JobState


class NinJobState(JobState):
    INACTIVE = float("-inf")
    MUDRA = {"Ten", "Chi", "Jin"}
    NINJUTSU_RESULTS = {
        "Fuma Shuriken", "Katon", "Raiton", "Hyoton", "Huton", "Doton",
        "Suiton", "Goka Mekkyaku", "Hyosho Ranryu",
    }
    MUDRA_RESULTS = {
        ("Ten",): "Fuma Shuriken",
        ("Chi",): "Fuma Shuriken",
        ("Jin",): "Fuma Shuriken",
        ("Chi", "Ten"): "Katon",
        ("Jin", "Ten"): "Katon",
        ("Ten", "Chi"): "Raiton",
        ("Jin", "Chi"): "Raiton",
        ("Ten", "Jin"): "Hyoton",
        ("Chi", "Jin"): "Hyoton",
        ("Jin", "Chi", "Ten"): "Huton",
        ("Chi", "Jin", "Ten"): "Huton",
        ("Ten", "Jin", "Chi"): "Doton",
        ("Jin", "Ten", "Chi"): "Doton",
        ("Ten", "Chi", "Jin"): "Suiton",
        ("Chi", "Ten", "Jin"): "Suiton",
    }
    KASSATSU_SKILLS = {
        "Fuma Shuriken", "Raiton", "Doton", "Suiton", "Huton",
        "Goka Mekkyaku", "Hyosho Ranryu",
    }
    BUNSHIN_WEAPONSKILLS = {
        "Spinning Edge", "Gust Slash", "Aeolian Edge", "Armor Crush",
        "Throwing Dagger", "Death Blossom", "Hakke Mujinsatsu",
        "Forked Raiju", "Fleeting Raiju",
    }
    BUNSHIN_AOE = {"Death Blossom", "Hakke Mujinsatsu"}
    NINKI_SPENDERS = {
        "Bhavacakra", "Zesho Meppo", "Hellfrog Medium",
        "Deathfrog Medium", "Bunshin",
    }
    RAIJU_SKILLS = {"Forked Raiju", "Fleeting Raiju"}
    RAIJU_BREAKERS = {
        "Spinning Edge", "Gust Slash", "Aeolian Edge", "Armor Crush",
        "Death Blossom", "Hakke Mujinsatsu",
    }
    HOLLOW_NOZUCHI_TRIGGERS = {
        "Hakke Mujinsatsu", "Katon", "Goka Mekkyaku", "Phantom Kamaitachi",
    }
    POSITIONAL_SKILLS = {"Aeolian Edge", "Armor Crush"}
    COMBO_WEAPONSKILLS = {
        "Spinning Edge", "Gust Slash", "Aeolian Edge",
        "Armor Crush", "Death Blossom", "Hakke Mujinsatsu",
    }

    def __init__(self, version="7.5"):
        super().__init__("NIN")
        self.version = version
        self.kassatsu_until = self.INACTIVE
        self.meisui_until = self.INACTIVE
        self.bunshin_stacks = 0
        self.bunshin_until = self.INACTIVE
        self.debuff_until = defaultdict(lambda: defaultdict(lambda: self.INACTIVE))
        self.mudra_sequence = []
        self.mudra_until = self.INACTIVE
        self.mudra_bunny = False
        self.tcj_sequence = []
        self.ten_chi_jin_until = self.INACTIVE
        self.ninki = 0
        self.kazematoi = 0
        self.shadow_walker_until = self.INACTIVE
        self.hidden_until = self.INACTIVE
        self.higi_until = self.INACTIVE
        self.tenri_ready_until = self.INACTIVE
        self.phantom_ready_until = self.INACTIVE
        self.raiju_stacks = 0
        self.raiju_until = self.INACTIVE
        self.true_north_until = self.INACTIVE
        self.doton_until = defaultdict(lambda: self.INACTIVE)
        self._pending_presses = {}
        self._doton_kassatsu_time = None

    def _version_at_least(self, version):
        return Decimal(str(self.version)) >= Decimal(str(version))

    @staticmethod
    def _raw_base(name):
        text = str(name or "")
        return text.rsplit(" (", 1)[0] if text.endswith(")") and " (" in text else text

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or self._raw_base(name)

    @staticmethod
    def _active(until, current_time):
        return until > current_time

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

    def _gain_ninki(self, amount, current_time, name):
        if self.ninki + amount > 100:
            self.warn(
                "nin_ninki_overcap",
                current_time,
                name,
                f"{name} overcaps Ninki by {self.ninki + amount - 100}.",
            )
        self.ninki = min(100, self.ninki + amount)

    def _spend_ninki(self, current_time, name):
        self.ninki = max(0, self.ninki - 50)

    def _expected_ninjutsu(self, sequence, kassatsu=False):
        expected = self.MUDRA_RESULTS.get(tuple(sequence))
        if kassatsu and expected == "Katon":
            return "Goka Mekkyaku"
        if kassatsu and expected == "Hyoton":
            return "Hyosho Ranryu"
        return expected

    @staticmethod
    def _tcj_mudra(name):
        for mudra in ("Ten", "Chi", "Jin"):
            if str(name).endswith(f"({mudra})"):
                return mudra
        return None

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Kassatsu", "Bunshin", "Ten Chi Jin", "Meisui"}

    def can_activate_without_target(self, name, skill):
        return self._canonical(name, skill) == "Doton"

    def _validate_ninjutsu(self, name, canonical, current_time, snapshot_time):
        in_tcj = self._active(self.ten_chi_jin_until, snapshot_time)
        if in_tcj:
            mudra = self._tcj_mudra(name)
            if mudra is None:
                self.warn(
                    "nin_tcj_missing_mudra_suffix",
                    current_time,
                    name,
                    f"{name} does not identify the Ten Chi Jin mudra button used.",
                )
                return True
            if mudra in self.tcj_sequence:
                self.warn(
                    "nin_tcj_mudra_duplicate",
                    current_time,
                    name,
                    f"{mudra} was repeated during Ten Chi Jin.",
                )
            self.tcj_sequence.append(mudra)
            expected = self._expected_ninjutsu(self.tcj_sequence)
            if canonical != expected:
                self.warn(
                    "nin_tcj_result_mismatch",
                    current_time,
                    name,
                    f"{tuple(self.tcj_sequence)} resolves to {expected}, not {canonical}.",
                )
            return True

        if self.mudra_until <= snapshot_time:
            self.mudra_sequence = []
            self.mudra_bunny = False
        if not self.mudra_sequence:
            self.warn(
                "nin_ninjutsu_without_mudra",
                current_time,
                name,
                f"{canonical} used without a tracked Mudra sequence.",
            )
            return False
        expected = None if self.mudra_bunny else self._expected_ninjutsu(
            self.mudra_sequence,
            kassatsu=self._active(self.kassatsu_until, snapshot_time),
        )
        if canonical != expected:
            self.warn(
                "nin_mudra_result_mismatch",
                current_time,
                name,
                f"{tuple(self.mudra_sequence)} resolves to {expected or 'Rabbit Medium'}, not {canonical}.",
            )
        return False

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        in_tcj = self._active(self.ten_chi_jin_until, snapshot_time)

        if canonical in self.MUDRA:
            if in_tcj:
                self.warn(
                    "nin_tcj_uses_result_actions",
                    current_time,
                    name,
                    "Ten Chi Jin expects the resolved actions such as Fuma Shuriken (Ten), not raw Mudra rows.",
                )
                return {}
            if self.mudra_until <= snapshot_time:
                self.mudra_sequence = []
                self.mudra_bunny = False
            if not self.mudra_sequence:
                self.mudra_until = current_time + 6.0
            if len(self.mudra_sequence) >= 3:
                self.warn(
                    "nin_mudra_overflow",
                    current_time,
                    name,
                    "More than three Mudra inputs were queued before a Ninjutsu result.",
                )
                self.mudra_bunny = True
            if canonical in self.mudra_sequence:
                self.warn(
                    "nin_mudra_duplicate",
                    current_time,
                    name,
                    f"{canonical} repeated inside one Mudra sequence.",
                )
                self.mudra_bunny = True
            self.mudra_sequence.append(canonical)
            return {}

        if self.mudra_sequence and canonical not in self.NINJUTSU_RESULTS:
            self.warn(
                "nin_mudra_interrupted",
                current_time,
                name,
                f"{canonical} was used between Mudra inputs and the Ninjutsu result.",
            )
            self.mudra_bunny = True

        is_tcj_result = False
        if canonical in self.NINJUTSU_RESULTS:
            is_tcj_result = self._validate_ninjutsu(name, canonical, current_time, snapshot_time)
            if canonical in {"Goka Mekkyaku", "Hyosho Ranryu"} and not self._active(
                self.kassatsu_until, snapshot_time
            ):
                self.warn(
                    "nin_kassatsu_required",
                    current_time,
                    name,
                    f"{canonical} requires Kassatsu.",
                )

        if in_tcj and canonical not in self.NINJUTSU_RESULTS:
            self.warn(
                "nin_tcj_action_locked",
                current_time,
                name,
                f"{canonical} is not a Ninjutsu action allowed during Ten Chi Jin.",
            )
        if canonical == "Ten Chi Jin" and self._active(self.kassatsu_until, current_time):
            self.warn(
                "nin_tcj_during_kassatsu",
                current_time,
                name,
                "Ten Chi Jin cannot be executed while Kassatsu is active.",
            )
        if canonical == "Kassatsu" and in_tcj:
            self.warn(
                "nin_kassatsu_during_tcj",
                current_time,
                name,
                "Kassatsu cannot be executed during Ten Chi Jin.",
            )

        if canonical in self.NINKI_SPENDERS and self.ninki < 50:
            self.warn(
                "nin_ninki_low",
                current_time,
                name,
                f"{canonical} used with Ninki {self.ninki}; expected at least 50.",
            )
        if canonical == "Kunai's Bane" and not (
            self._active(self.shadow_walker_until, current_time)
            or self._active(self.hidden_until, current_time)
        ):
            self.warn(
                "nin_shadow_walker_missing",
                current_time,
                name,
                f"{canonical} requires Hidden or Shadow Walker.",
            )
        if canonical == "Meisui" and not self._active(
            self.shadow_walker_until, current_time
        ):
            self.warn(
                "nin_shadow_walker_missing",
                current_time,
                name,
                "Meisui requires Shadow Walker.",
            )
        if canonical == "Phantom Kamaitachi" and not self._active(
            self.phantom_ready_until, current_time
        ):
            self.warn(
                "nin_phantom_not_ready",
                current_time,
                name,
                "Phantom Kamaitachi used without Phantom Kamaitachi Ready.",
            )
        if canonical in self.RAIJU_SKILLS and not (
            self.raiju_stacks > 0 and self._active(self.raiju_until, current_time)
        ):
            self.warn(
                "nin_raiju_not_ready",
                current_time,
                name,
                f"{canonical} used without Raiju Ready.",
            )
        if canonical in {"Zesho Meppo", "Deathfrog Medium"} and not self._active(
            self.higi_until, current_time
        ):
            self.warn(
                "nin_higi_not_ready",
                current_time,
                name,
                f"{canonical} requires Higi from Dokumori.",
            )
        if canonical == "Tenri Jindo" and not self._active(
            self.tenri_ready_until, current_time
        ):
            self.warn(
                "nin_tenri_not_ready",
                current_time,
                name,
                "Tenri Jindo used without Tenri Jindo Ready.",
            )

        is_combo = self.is_combo(name, skill, current_time, {})
        positional_hit = self._event_context.get("positional_hit")
        if canonical in self.POSITIONAL_SKILLS:
            positional_hit = positional_hit is not False or self._active(
                self.true_north_until, current_time
            )
        else:
            positional_hit = True
        bunshin_applied = (
            canonical in self.BUNSHIN_WEAPONSKILLS
            and self.bunshin_stacks > 0
            and self._active(self.bunshin_until, current_time)
        )
        pending = {
            "canonical": canonical,
            "is_combo": is_combo,
            "is_tcj_result": is_tcj_result,
            "bunshin_applied": bunshin_applied,
            "kassatsu_applied": (
                canonical in self.KASSATSU_SKILLS
                and self._active(self.kassatsu_until, snapshot_time)
                and not is_tcj_result
            ),
            "meisui_applied": (
                canonical in {"Bhavacakra", "Zesho Meppo"}
                and self._active(self.meisui_until, current_time)
            ),
            "kazematoi_applied": canonical == "Aeolian Edge" and self.kazematoi > 0,
            "positional_hit": positional_hit,
        }
        self._pending_presses[(name, current_time)] = pending
        return {
            "nin_is_combo": is_combo,
            "nin_bunshin_applied": bunshin_applied,
            "nin_kassatsu_applied": pending["kassatsu_applied"],
            "nin_meisui_applied": pending["meisui_applied"],
            "nin_kazematoi_applied": pending["kazematoi_applied"],
            "positional_hit": positional_hit,
        }

    def on_press_confirmed(self, name, skill, current_time, payload):
        pending = self._pending_presses.pop((name, current_time), None) or {
            "canonical": self._canonical(name, skill),
            "is_combo": self.is_combo(name, skill, current_time, payload),
            "is_tcj_result": False,
            "bunshin_applied": False,
            "kassatsu_applied": False,
            "meisui_applied": False,
            "kazematoi_applied": False,
        }
        canonical = pending["canonical"]
        is_combo = pending["is_combo"]

        if canonical in self.NINKI_SPENDERS:
            self._spend_ninki(current_time, canonical)
        if canonical == "Dokumori":
            self._gain_ninki(40, current_time, canonical)
            self.higi_until = current_time + 30.0
        elif canonical == "Meisui":
            self._gain_ninki(50, current_time, canonical)
            self.meisui_until = current_time + 30.0
            self.shadow_walker_until = self.INACTIVE
            self.hidden_until = self.INACTIVE
        elif canonical == "Bunshin":
            self.bunshin_stacks = 5
            self.bunshin_until = current_time + 30.0
            self.phantom_ready_until = current_time + 45.0
        elif canonical == "Kassatsu":
            self.kassatsu_until = current_time + 15.0
        elif canonical == "Ten Chi Jin":
            self.ten_chi_jin_until = current_time + 6.0
            self.tenri_ready_until = current_time + 30.0
            self.tcj_sequence = []
            self.mudra_sequence = []
            self.mudra_bunny = False
        elif canonical == "True North":
            self.true_north_until = current_time + 10.0
        elif canonical == "Hide":
            self.hidden_until = float("inf")
            self.doton_until.clear()

        if canonical == "Kunai's Bane":
            self.shadow_walker_until = self.INACTIVE
            self.hidden_until = self.INACTIVE
        elif canonical == "Trick Attack":
            self.shadow_walker_until = self.INACTIVE
            self.hidden_until = self.INACTIVE

        ninki_gain = 0
        if canonical in {"Spinning Edge", "Throwing Dagger", "Death Blossom"}:
            ninki_gain = 5
        elif canonical == "Gust Slash" and is_combo:
            ninki_gain = 5
        elif canonical in {"Aeolian Edge", "Armor Crush"} and is_combo:
            ninki_gain = 15
        elif canonical == "Hakke Mujinsatsu" and is_combo:
            ninki_gain = 5
        elif canonical in self.RAIJU_SKILLS:
            ninki_gain = 5
        elif canonical == "Phantom Kamaitachi":
            ninki_gain = 10
        if pending["bunshin_applied"]:
            ninki_gain += 5
            self.bunshin_stacks = max(0, self.bunshin_stacks - 1)
        if ninki_gain:
            self._gain_ninki(ninki_gain, current_time, canonical)

        if canonical == "Armor Crush" and is_combo:
            self.kazematoi = min(5, self.kazematoi + 2)
        elif pending["kazematoi_applied"]:
            self.kazematoi -= 1

        if canonical == "Raiton":
            self.raiju_stacks = min(3, self.raiju_stacks + 1)
            self.raiju_until = current_time + 30.0
        elif canonical in self.RAIJU_SKILLS:
            self.raiju_stacks = max(0, self.raiju_stacks - 1)
        elif canonical in self.RAIJU_BREAKERS and self.raiju_stacks:
            self.raiju_stacks = 0
            self.raiju_until = self.INACTIVE

        if canonical in {"Suiton", "Huton"}:
            self.shadow_walker_until = current_time + 20.0
        if canonical in {"Zesho Meppo", "Deathfrog Medium"}:
            self.higi_until = self.INACTIVE
        if canonical == "Tenri Jindo":
            self.tenri_ready_until = self.INACTIVE
        if canonical == "Phantom Kamaitachi":
            self.phantom_ready_until = self.INACTIVE

        if pending["meisui_applied"]:
            self.meisui_until = self.INACTIVE
        if pending["kassatsu_applied"]:
            self.kassatsu_until = self.INACTIVE
        if canonical in self.NINJUTSU_RESULTS:
            if pending["is_tcj_result"]:
                if len(self.tcj_sequence) >= 3:
                    self.ten_chi_jin_until = self.INACTIVE
            else:
                self.mudra_sequence = []
                self.mudra_bunny = False
                self.mudra_until = self.INACTIVE

        if self._active(self.hidden_until, current_time) and canonical not in {
            "Hide", "Kunai's Bane", "Trick Attack", "Sprint",
        }:
            self.hidden_until = self.INACTIVE

    def resolve_potency(self, name, skill, current_time, payload):
        potency, is_combo = super().resolve_potency(name, skill, current_time, payload)
        canonical = self._canonical(name, skill)

        if canonical == "Doton":
            potency = 0
        if canonical in self.POSITIONAL_SKILLS and payload.get("positional_hit") is False:
            potency = max(0, potency - 60)
        if payload.get("nin_kazematoi_applied"):
            potency += 100
        if payload.get("nin_meisui_applied"):
            potency += 150
        if payload.get("nin_kassatsu_applied") and canonical != "Doton":
            potency = int(round(potency * 1.3))
        if canonical == "Doton" and payload.get("nin_kassatsu_applied"):
            self._doton_kassatsu_time = current_time

        return potency, is_combo

    def _apply_debuff(self, name, target_id, current_time):
        durations = {
            "Dokumori": 21.0,
            "Kunai's Bane": 16.25,
            "Trick Attack": 15.77,
        }
        if name in durations:
            self.debuff_until[target_id][name] = current_time + durations[name]

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        canonical = self._canonical(name, skill)
        if canonical in self.COMBO_WEAPONSKILLS:
            super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        if canonical == "Doton":
            for target_id in self._affected_target_ids(payload):
                self.doton_until[target_id] = current_time + 18.0
        if payload.get("damage_immune"):
            return
        for target_id in self._affected_target_ids(payload):
            self._apply_debuff(canonical, target_id, current_time)

    def is_dot_active(self, dot, current_time):
        if dot.get("dot_key") == "Doton":
            return self._active(self.doton_until[dot.get("tid", 1)], current_time)
        return True

    def dot_applications(self, name, skill, current_time, target_count, target_id,
                         active_buffs, has_potion):
        applications = super().dot_applications(
            name, skill, current_time, target_count, target_id, active_buffs, has_potion
        )
        if self._canonical(name, skill) == "Doton" and self._doton_kassatsu_time == current_time:
            for application in applications:
                application["potency"] = int(round(application["potency"] * 1.3))
            self._doton_kassatsu_time = None
        return applications

    def followup_damage_events(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        events = []
        if canonical == "Dream Within a Dream":
            potency = skill.get("potency", 0)
            shared_roll = {}
            if payload.get("source_roll_available"):
                source_crit = bool(payload.get("source_crit"))
                source_dh = bool(payload.get("source_dh"))
                shared_roll = {
                    "guaranteed_crit": source_crit,
                    "force_no_crit": not source_crit,
                    "guaranteed_dh": source_dh,
                    "force_no_dh": not source_dh,
                }
            events.extend([
                {"name": canonical, "potency": potency, "delay": 0.15, "targets": 1, **shared_roll},
                {"name": canonical, "potency": potency, "delay": 0.30, "targets": 1, **shared_roll},
            ])
        if payload.get("nin_bunshin_applied"):
            is_aoe = canonical in self.BUNSHIN_AOE
            events.append({
                "name": f"{canonical} (pet)",
                "potency": 80 if is_aoe else 160,
                "delay": 0.088,
                "targets": payload.get("targets", 1) if is_aoe else 1,
                "is_aoe": is_aoe,
                "decay": 0.0,
                "job_mod_override": 100,
                "extends_duration": False,
            })
        target_id = payload.get("tid", 1)
        hollow_trigger = (
            canonical in self.HOLLOW_NOZUCHI_TRIGGERS
            and self._active(self.doton_until[target_id], current_time)
            and (canonical != "Hakke Mujinsatsu" or payload.get("nin_is_combo"))
        )
        if hollow_trigger:
            events.append({
                "name": "Hollow Nozuchi",
                "potency": 70 if self._version_at_least("7.25") else 50,
                "delay": 0.0,
                "targets": payload.get("targets", 1),
                "is_aoe": True,
                "decay": 0.0,
            })
        return events

    def active_damage_buffs(self, t, target_id=None):
        target_id = target_id or 1
        debuffs = self.debuff_until[target_id]
        has_dokumori = debuffs["Dokumori"] > t
        has_kunai = debuffs["Kunai's Bane"] > t
        has_trick = debuffs["Trick Attack"] > t
        damage_mult = 1.0
        damage_factors = []
        if has_dokumori:
            damage_mult *= 1.05
            damage_factors.append(("介毒", 1.05))
        if has_kunai:
            damage_mult *= 1.10
            damage_factors.append(("百雷铳", 1.10))
        if has_trick:
            damage_mult *= 1.10
            damage_factors.append(("攻其不备", 1.10))
        return {
            "nin_dokumori": has_dokumori,
            "nin_kunai": has_kunai,
            "nin_trick": has_trick,
            "damage_mult": damage_mult,
            "damage_factors": damage_factors,
        }

    def auto_attack_interval_multiplier(self, t):
        return 0.85

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("nin_dokumori"):
            labels.append("毒盛")
        if active_buffs.get("nin_kunai"):
            labels.append("百雷铳")
        if active_buffs.get("nin_trick"):
            labels.append("攻其不备")
        if has_potion:
            labels.append("药")
        return labels
