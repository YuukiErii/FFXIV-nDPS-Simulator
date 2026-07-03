try:
    from .base import JobState
except ImportError:
    from base import JobState


class BrdJobState(JobState):
    SONGS = {
        "Mage's Ballad": "mage",
        "Army's Paeon": "army",
        "The Wanderer's Minuet": "wanderer",
    }
    RADIANT_MULT = {1: 1.02, 2: 1.04, 3: 1.06}
    RADIANT_ENCORE_POTENCY = {1: 700, 2: 800, 3: 1100}
    PITCH_PERFECT_POTENCY = {1: 100, 2: 220, 3: 360}
    ARMY_MUSE_MULT = {1: 0.99, 2: 0.98, 3: 0.96, 4: 0.88}

    def __init__(self):
        super().__init__("BRD")
        self.raging_until = -1.0
        self.battle_voice_start = -1.0
        self.battle_voice_until = -1.0
        self.radiant_start = -1.0
        self.radiant_until = -1.0
        self.radiant_mult = 1.0
        self.radiant_encore_coda = 3
        self.radiant_encore_until = -1.0
        self.song = None
        self.song_until = -1.0
        self.coda = set()
        self.pitch_stacks = 0
        self.army_stacks = 0
        self.army_muse_until = -1.0
        self.army_muse_mult = 1.0
        self.army_ethos_until = -1.0
        self.army_ethos_stacks = 0
        self.soul_voice = 100
        self.barrage_until = -1.0
        self.blast_arrow_until = -1.0
        self.resonant_arrow_until = -1.0
        self.caustic_until = -1.0
        self.storm_until = -1.0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {
            "Raging Strikes", "Battle Voice", "Radiant Finale",
            "Mage's Ballad", "Army's Paeon", "The Wanderer's Minuet", "Barrage",
        }

    def _sync_army_ethos(self, current_time):
        if self.song == "Army's Paeon" and not self._active_until(self.song_until, current_time) and self.army_stacks > 0:
            self.army_ethos_stacks = self.army_stacks
            self.army_ethos_until = self.song_until + 30.0
            self.army_stacks = 0

    def _grant_army_muse(self, current_time, stacks):
        stacks = max(1, min(4, int(stacks or 0)))
        self.army_muse_mult = self.ARMY_MUSE_MULT[stacks]
        self.army_muse_until = current_time + 10.0
        self.army_ethos_until = -1.0
        self.army_ethos_stacks = 0

    def on_press_confirmed(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Raging Strikes":
            self.raging_until = current_time + 20.0
            payload["brd_buff_confirmed"] = canonical
        elif canonical == "Battle Voice":
            self.battle_voice_start, self.battle_voice_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
            payload["brd_buff_confirmed"] = canonical
        elif canonical == "Radiant Finale":
            coda_count = max(1, min(3, len(self.coda)))
            self.radiant_mult = self.RADIANT_MULT[coda_count]
            self.radiant_start, self.radiant_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
            self.radiant_encore_coda = coda_count
            self.radiant_encore_until = current_time + 30.0
            self.coda.clear()
            payload["brd_buff_confirmed"] = canonical
        elif canonical in self.SONGS:
            self._begin_song(canonical, current_time)
            payload["brd_buff_confirmed"] = canonical
        elif canonical == "Barrage":
            self.barrage_until = current_time + 10.0
            self.resonant_arrow_until = current_time + 30.0
            payload["brd_buff_confirmed"] = canonical

    def resolve_potency(self, name, skill, current_time, payload):
        canonical = self._canonical(name, skill)
        if canonical == "Apex Arrow":
            gauge = self.soul_voice if self.soul_voice >= 20 else 100
            return int(round(gauge * 7)), False
        if canonical == "Radiant Encore":
            coda = max(1, min(3, self.radiant_encore_coda))
            return self.RADIANT_ENCORE_POTENCY[coda], False
        if canonical == "Pitch Perfect":
            stacks = 3
            return self.PITCH_PERFECT_POTENCY[max(1, min(3, stacks))], False
        if canonical == "Refulgent Arrow" and self._active_until(self.barrage_until, current_time):
            return skill.get("potency", 0) * 3, False
        if canonical == "Shadowbite" and self._active_until(self.barrage_until, current_time):
            return 300, False
        return super().resolve_potency(name, skill, current_time, payload)

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        self._sync_army_ethos(current_time)
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if (payload.get("press_time") is not None or payload.get("brd_buff_confirmed") == canonical) and canonical in {
            "Raging Strikes", "Battle Voice", "Radiant Finale",
            "Mage's Ballad", "Army's Paeon", "The Wanderer's Minuet", "Barrage",
        }:
            return
        if canonical == "Raging Strikes":
            self.raging_until = current_time + 20.0
        elif canonical == "Battle Voice":
            self.battle_voice_start, self.battle_voice_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
        elif canonical == "Radiant Finale":
            coda_count = max(1, min(3, len(self.coda)))
            self.radiant_mult = self.RADIANT_MULT[coda_count]
            self.radiant_start, self.radiant_until = self.party_buff_window(
                canonical, skill, current_time, 20.0
            )
            self.radiant_encore_coda = coda_count
            self.radiant_encore_until = current_time + 30.0
            self.coda.clear()
        elif canonical in self.SONGS:
            self._begin_song(canonical, current_time)
        elif canonical == "Barrage":
            self.barrage_until = current_time + 10.0
            self.resonant_arrow_until = current_time + 30.0
        elif canonical == "Empyreal Arrow" and self._active_until(self.song_until, current_time):
            self.soul_voice = min(100, self.soul_voice + 5)
            if self.song == "The Wanderer's Minuet":
                self.pitch_stacks = min(3, self.pitch_stacks + 1)
            elif self.song == "Army's Paeon":
                self.army_stacks = min(4, self.army_stacks + 1)
        elif canonical == "Pitch Perfect":
            self.pitch_stacks = 0
        elif canonical == "Apex Arrow":
            gauge = self.soul_voice if self.soul_voice >= 20 else 100
            if gauge >= 80:
                self.blast_arrow_until = current_time + 10.0
            self.soul_voice = 0
        elif canonical == "Blast Arrow":
            self.blast_arrow_until = -1.0
        elif canonical == "Resonant Arrow":
            self.resonant_arrow_until = -1.0
        elif canonical == "Radiant Encore":
            self.radiant_encore_until = -1.0
        elif canonical == "Caustic Bite":
            self.caustic_until = current_time + skill.get("dot_duration", 45.0)
        elif canonical == "Stormbite":
            self.storm_until = current_time + skill.get("dot_duration", 45.0)
        elif canonical == "Iron Jaws" and (
                self._active_until(self.caustic_until, current_time)
                or self._active_until(self.storm_until, current_time)):
            duration = skill.get("dot_duration", 45.0)
            if self._active_until(self.caustic_until, current_time):
                self.caustic_until = current_time + duration
            if self._active_until(self.storm_until, current_time):
                self.storm_until = current_time + duration
        if canonical in {"Refulgent Arrow", "Shadowbite"}:
            self.barrage_until = -1.0

    def _begin_song(self, canonical, current_time):
        if canonical in {"Mage's Ballad", "The Wanderer's Minuet"}:
            if self.song == "Army's Paeon" and self._active_until(self.song_until, current_time) and self.army_stacks > 0:
                self._grant_army_muse(current_time, self.army_stacks)
            elif self._active_until(self.army_ethos_until, current_time):
                self._grant_army_muse(current_time, self.army_ethos_stacks)
        self.song = canonical
        self.song_until = current_time + 45.0
        self.coda.add(self.SONGS[canonical])
        self.pitch_stacks = 0
        self.army_stacks = 0

    def _dot_payload(self, source_name, dot_name, dot_key, potency, current_time, target_count,
                     target_id, active_buffs, has_potion, duration=45.0):
        return {
            "name": dot_name,
            "source_name": source_name,
            "dot_key": dot_key,
            "tid": target_id,
            "targets": 1,
            "potency": potency,
            "buffs": active_buffs,
            "expire": current_time + duration,
            "has_potion": has_potion,
            "guaranteed_crit": False,
            "guaranteed_dh": False,
        }

    def dot_applications(self, name, skill, current_time, target_count, target_id, active_buffs, has_potion):
        canonical = self._canonical(name, skill)
        duration = skill.get("dot_duration", 45.0)
        if canonical == "Caustic Bite":
            return [self._dot_payload(name, "Caustic Bite (dot)", "brd_caustic", 20, current_time,
                                      target_count, target_id, active_buffs, has_potion, duration)]
        if canonical == "Stormbite":
            return [self._dot_payload(name, "Stormbite (dot)", "brd_storm", 25, current_time,
                                      target_count, target_id, active_buffs, has_potion, duration)]
        if canonical == "Iron Jaws":
            out = []
            if self._active_until(self.caustic_until, current_time):
                out.append(self._dot_payload(name, "Caustic Bite (dot)", "brd_caustic", 20, current_time,
                                             target_count, target_id, active_buffs, has_potion, duration))
            if self._active_until(self.storm_until, current_time):
                out.append(self._dot_payload(name, "Stormbite (dot)", "brd_storm", 25, current_time,
                                             target_count, target_id, active_buffs, has_potion, duration))
            if out:
                return out
            self.warn("brd_iron_jaws_missing_dot", current_time, name,
                      "Iron Jaws used without an active Caustic Bite or Stormbite; DoT refresh skipped.")
            return []
        return super().dot_applications(name, skill, current_time, target_count, target_id, active_buffs, has_potion)

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        damage_factors = []
        crit_rate_add = 0.0
        dh_rate_add = 0.0
        raging = self._active_until(self.raging_until, t)
        radiant = self._active_window(self.radiant_start, self.radiant_until, t)
        song_active = self._active_until(self.song_until, t)
        battle_voice = self._active_window(self.battle_voice_start, self.battle_voice_until, t)
        if raging:
            damage_mult *= 1.15
            damage_factors.append(("猛者强击", 1.15))
        if radiant:
            damage_mult *= self.radiant_mult
            damage_factors.append(("光明神", self.radiant_mult))
        if song_active:
            if self.song == "Mage's Ballad":
                damage_mult *= 1.01
                damage_factors.append(("贤者歌", 1.01))
            elif self.song == "Army's Paeon":
                dh_rate_add += 0.03
            elif self.song == "The Wanderer's Minuet":
                crit_rate_add += 0.02
        if battle_voice:
            dh_rate_add += 0.20
        return {
            "brd_raging": raging,
            "brd_battle_voice": battle_voice,
            "brd_radiant": radiant,
            "brd_song": self.song if song_active else None,
            "damage_mult": damage_mult,
            "damage_factors": damage_factors,
            "crit_rate_add": crit_rate_add,
            "dh_rate_add": dh_rate_add,
        }

    def auto_attack_interval_multiplier(self, t):
        self._sync_army_ethos(t)
        if self._active_until(self.army_muse_until, t):
            return self.army_muse_mult
        if self.song == "Army's Paeon" and self._active_until(self.song_until, t) and self.army_stacks > 0:
            return max(0.84, 1.0 - 0.04 * self.army_stacks)
        return 1.0

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("brd_raging"):
            labels.append("猛者")
        if active_buffs.get("brd_battle_voice"):
            labels.append("战斗之声")
        if active_buffs.get("brd_radiant"):
            labels.append("最终乐章")
        if active_buffs.get("brd_song"):
            labels.append("歌")
        if has_potion:
            labels.append("药")
        return labels
