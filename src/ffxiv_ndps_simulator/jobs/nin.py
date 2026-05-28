from collections import defaultdict

try:
    from .base import JobState
except ImportError:
    from base import JobState


class NinJobState(JobState):
    BUFFED_BY_BUNSHIN = {
        "Spinning Edge", "Gust Slash", "Aeolian Edge", "Armor Crush",
        "Throwing Dagger", "Death Blossom", "Hakke Mujinsatsu",
        "Forked Raiju", "Fleeting Raiju",
    }
    AOE_BUNSHIN = {"Death Blossom", "Hakke Mujinsatsu"}
    KASSATSU_SKILLS = {"Hyosho Ranryu", "Goka Mekkyaku", "Doton", "Doton (Chi)"}

    def __init__(self):
        super().__init__("NIN")
        self.kassatsu_until = -1.0
        self.meisui_until = -1.0
        self.bunshin_stacks = 0
        self.bunshin_until = -1.0
        self.debuff_until = defaultdict(lambda: defaultdict(lambda: -1.0))
        self.mudra_sequence = []
        self.ten_chi_jin_until = -1.0
        self.ninki = 0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return name in {"Kassatsu", "Bunshin", "Ten Chi Jin", "Meisui"}

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        if canonical in {"Ten", "Chi", "Jin"}:
            if len(self.mudra_sequence) >= 3:
                self.warn("nin_mudra_overflow", current_time, name,
                          "More than three Mudra inputs were queued before a Ninjutsu result.")
            elif canonical in self.mudra_sequence:
                self.warn("nin_mudra_duplicate", current_time, name,
                          f"{canonical} repeated inside one Mudra sequence.")
            self.mudra_sequence.append(canonical)
            return {}

        ninjutsu_results = {
            "Fuma Shuriken", "Fuma Shuriken (Ten)", "Fuma Shuriken (Chi)", "Fuma Shuriken (Jin)",
            "Raiton", "Raiton (Chi)", "Suiton", "Suiton (Jin)", "Hyosho Ranryu",
            "Goka Mekkyaku", "Katon", "Katon (Ten)", "Doton", "Doton (Chi)", "Huton",
            "Huton (Ten)", "Hyoton", "Hyoton (Jin)",
        }
        if canonical in ninjutsu_results and not self.mudra_sequence and self.ten_chi_jin_until <= snapshot_time:
            self.warn("nin_ninjutsu_without_mudra", current_time, name,
                      f"{canonical} used without a tracked Mudra sequence.")
        if canonical in {"Bhavacakra", "Zesho Meppo", "Bunshin"} and self.ninki < 50:
            self.warn("nin_ninki_low", current_time, name,
                      f"{canonical} used with Ninki {self.ninki}; expected at least 50.")
        return {}

    def on_press_complete(self, name, current_time):
        if name == "Kassatsu":
            self.kassatsu_until = current_time + 15.0
        elif name == "Meisui":
            self.meisui_until = current_time + 30.0
        elif name == "Bunshin":
            self.bunshin_stacks = 5
            self.bunshin_until = current_time + 30.7
        elif name == "Ten Chi Jin":
            self.ten_chi_jin_until = current_time + 6.0

    def _has_bunshin(self, current_time):
        return self.bunshin_stacks > 0 and self.bunshin_until > current_time

    def resolve_potency(self, name, skill, current_time, payload):
        potency, is_combo = super().resolve_potency(name, skill, current_time, payload)

        if name == "Dream Within a Dream":
            potency = 540
        elif name == "Dokumori":
            potency = 400
        elif name == "Kunai's Bane":
            potency = 700
        elif name == "Phantom Kamaitachi":
            potency = 630

        if name in {"Bhavacakra", "Zesho Meppo"} and self.meisui_until > current_time:
            potency += 150
            payload["nin_meisui_applied"] = True

        if name in self.KASSATSU_SKILLS and self.kassatsu_until > current_time:
            potency = int(round(potency * 1.3))
            payload["nin_kassatsu_applied"] = True

        if name in self.BUFFED_BY_BUNSHIN and self._has_bunshin(current_time):
            potency += 72 if name in self.AOE_BUNSHIN or skill.get("is_aoe") else 144
            payload["nin_bunshin_applied"] = True

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
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        target_id = payload.get("tid", 1)
        self._apply_debuff(name, target_id, current_time)
        if payload.get("nin_bunshin_applied"):
            self.bunshin_stacks = max(0, self.bunshin_stacks - 1)
        if payload.get("nin_kassatsu_applied"):
            self.kassatsu_until = -1.0
        if payload.get("nin_meisui_applied"):
            self.meisui_until = -1.0
        canonical = self._canonical(name, skill)
        if canonical in {
            "Fuma Shuriken", "Fuma Shuriken (Ten)", "Fuma Shuriken (Chi)", "Fuma Shuriken (Jin)",
            "Raiton", "Raiton (Chi)", "Suiton", "Suiton (Jin)", "Hyosho Ranryu",
            "Goka Mekkyaku", "Katon", "Katon (Ten)", "Doton", "Doton (Chi)", "Huton",
            "Huton (Ten)", "Hyoton", "Hyoton (Jin)",
        }:
            self.mudra_sequence = []
        if canonical in {"Aeolian Edge", "Armor Crush", "Hakke Mujinsatsu"} and is_combo:
            self.ninki = min(100, self.ninki + 15)
        elif canonical in {"Dokumori", "Mug"}:
            self.ninki = min(100, self.ninki + 40)
        elif canonical == "Meisui":
            self.ninki = min(100, self.ninki + 50)
        elif canonical in {"Bhavacakra", "Zesho Meppo", "Bunshin"}:
            self.ninki = max(0, self.ninki - 50)

    def active_damage_buffs(self, t, target_id=None):
        target_id = target_id or 1
        debuffs = self.debuff_until[target_id]
        has_dokumori = debuffs["Dokumori"] > t
        has_kunai = debuffs["Kunai's Bane"] > t
        has_trick = debuffs["Trick Attack"] > t
        damage_mult = 1.0
        if has_dokumori:
            damage_mult *= 1.05
        if has_kunai:
            damage_mult *= 1.10
        if has_trick:
            damage_mult *= 1.10
        return {
            "nin_dokumori": has_dokumori,
            "nin_kunai": has_kunai,
            "nin_trick": has_trick,
            "damage_mult": damage_mult,
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
