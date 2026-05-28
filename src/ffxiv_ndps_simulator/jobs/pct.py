try:
    from .base import JobState
except ImportError:
    from base import JobState


class PctJobState(JobState):
    def __init__(self):
        super().__init__("PCT")
        self.starry_muse_until = -1.0
        self.creature_motifs = set()
        self.weapon_motif_ready = False
        self.landscape_motif_ready = False
        self.hammer_stacks = 0

    def handles_skill_buff(self, name, skill):
        return name == "Starry Muse"

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        muse_requirements = {
            "Pom Muse": "pom",
            "Winged Muse": "wing",
            "Clawed Muse": "claw",
            "Fanged Muse": "maw",
        }
        required = muse_requirements.get(canonical)
        if required and required not in self.creature_motifs:
            self.warn("pct_creature_motif_missing", current_time, name,
                      f"{canonical} used without the tracked {required} motif.")
        if canonical == "Striking Muse" and not self.weapon_motif_ready:
            self.warn("pct_weapon_motif_missing", current_time, name,
                      "Striking Muse used without a tracked Weapon/Hammer Motif.")
        if canonical == "Starry Muse" and not self.landscape_motif_ready:
            self.warn("pct_landscape_motif_missing", current_time, name,
                      "Starry Muse used without a tracked Landscape/Starry Sky Motif.")
        if canonical in {"Hammer Stamp", "Hammer Brush", "Polishing Hammer"} and self.hammer_stacks <= 0:
            self.warn("pct_hammer_stack_low", current_time, name,
                      f"{canonical} used without a tracked Hammer stack.")
        if canonical == "Star Prism" and self.starry_muse_until <= snapshot_time:
            self.warn("pct_starry_muse_inactive", current_time, name,
                      "Star Prism used outside a tracked Starry Muse window.")
        return {}

    def on_press_complete(self, name, current_time):
        canonical = self._canonical(name)
        if canonical == "Starry Muse":
            self.starry_muse_until = current_time + 20.5
            self.landscape_motif_ready = False
        elif canonical in {"Pom Motif", "Creature Motif"}:
            self.creature_motifs.add("pom")
        elif canonical == "Wing Motif":
            self.creature_motifs.add("wing")
        elif canonical == "Claw Motif":
            self.creature_motifs.add("claw")
        elif canonical == "Maw Motif":
            self.creature_motifs.add("maw")
        elif canonical in {"Weapon Motif", "Hammer Motif"}:
            self.weapon_motif_ready = True
        elif canonical in {"Landscape Motif", "Starry Sky Motif"}:
            self.landscape_motif_ready = True
        elif canonical == "Striking Muse":
            self.weapon_motif_ready = False
            self.hammer_stacks = 3
        elif canonical in {"Hammer Stamp", "Hammer Brush", "Polishing Hammer"}:
            self.hammer_stacks = max(0, self.hammer_stacks - 1)
        elif canonical == "Pom Muse":
            self.creature_motifs.discard("pom")
        elif canonical == "Winged Muse":
            self.creature_motifs.discard("wing")
        elif canonical == "Clawed Muse":
            self.creature_motifs.discard("claw")
        elif canonical == "Fanged Muse":
            self.creature_motifs.discard("maw")

    def active_damage_buffs(self, t, target_id=None):
        is_starry = self.starry_muse_until > t
        return {
            "pct_starry_muse": is_starry,
            "damage_mult": 1.05 if is_starry else 1.0,
        }

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("pct_starry_muse"):
            labels.append("星空构想")
        if has_potion:
            labels.append("药")
        return labels
