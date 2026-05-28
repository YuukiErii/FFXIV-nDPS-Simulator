try:
    from .base import JobState
except ImportError:
    from base import JobState


class BrdJobState(JobState):
    def __init__(self):
        super().__init__("BRD")
        self.raging_until = -1.0
        self.battle_voice_until = -1.0
        self.radiant_until = -1.0
        self.song = None
        self.song_until = -1.0
        self.caustic_until = -1.0
        self.storm_until = -1.0

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) in {"Raging Strikes", "Battle Voice", "Radiant Finale"}

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        super().on_damage_resolved(name, skill, current_time, is_combo, payload)
        canonical = self._canonical(name, skill)
        if canonical == "Raging Strikes":
            self.raging_until = current_time + 20.0
        elif canonical == "Battle Voice":
            self.battle_voice_until = current_time + 20.0
        elif canonical == "Radiant Finale":
            self.radiant_until = current_time + 30.0
        elif canonical in {"The Wanderer's Minuet", "Mage's Ballad", "Army's Paeon"}:
            self.song = canonical
            self.song_until = current_time + 45.0
        elif canonical == "Caustic Bite":
            self.caustic_until = current_time + skill.get("dot_duration", 45.0)
        elif canonical == "Stormbite":
            self.storm_until = current_time + skill.get("dot_duration", 45.0)
        elif canonical == "Iron Jaws" and self.caustic_until > current_time and self.storm_until > current_time:
            duration = skill.get("dot_duration", 45.0)
            self.caustic_until = current_time + duration
            self.storm_until = current_time + duration

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
            if self.caustic_until > current_time and self.storm_until > current_time:
                return [
                    self._dot_payload(name, "Caustic Bite (dot)", "brd_caustic", 20, current_time,
                                      target_count, target_id, active_buffs, has_potion, duration),
                    self._dot_payload(name, "Stormbite (dot)", "brd_storm", 25, current_time,
                                      target_count, target_id, active_buffs, has_potion, duration),
                ]
            self.warn("brd_iron_jaws_missing_dot", current_time, name,
                      "Iron Jaws used without both Caustic Bite and Stormbite active; DoT refresh skipped.")
            return []
        return super().dot_applications(name, skill, current_time, target_count, target_id, active_buffs, has_potion)

    def active_damage_buffs(self, t, target_id=None):
        damage_mult = 1.0
        if self.raging_until > t:
            damage_mult *= 1.15
        return {
            "brd_raging": self.raging_until > t,
            "brd_battle_voice": self.battle_voice_until > t,
            "brd_radiant": self.radiant_until > t,
            "brd_song": self.song if self.song_until > t else None,
            "damage_mult": damage_mult,
            "dh_rate_add": 0.20 if self.battle_voice_until > t else 0.0,
        }

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
