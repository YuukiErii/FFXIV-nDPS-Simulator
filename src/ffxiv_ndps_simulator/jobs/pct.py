try:
    from .base import JobState
except ImportError:
    from base import JobState


class PctJobState(JobState):
    CREATURE_MUSE_REQUIREMENTS = {
        "Pom Muse": "pom",
        "Winged Muse": "wing",
        "Clawed Muse": "claw",
        "Fanged Muse": "maw",
    }
    HAMMER_CHAIN = {
        "Hammer Stamp": "Hammer Brush",
        "Hammer Brush": "Polishing Hammer",
        "Polishing Hammer": None,
    }
    HYPERPHANTASIA_CONSUMERS = {
        "Fire in Red", "Aero in Green", "Water in Blue",
        "Fire II in Red", "Aero II in Green", "Water II in Blue",
        "Blizzard in Cyan", "Blizzard II in Cyan", "Stone in Yellow",
        "Stone II in Yellow", "Thunder in Magenta", "Thunder II in Magenta",
        "Holy in White", "Comet in Black", "Star Prism",
    }
    NORMAL_HUE_REQUIREMENTS = {
        "Fire in Red": 0,
        "Fire II in Red": 0,
        "Aero in Green": 1,
        "Aero II in Green": 1,
        "Water in Blue": 2,
        "Water II in Blue": 2,
    }
    SUBTRACTIVE_HUE_REQUIREMENTS = {
        "Blizzard in Cyan": 0,
        "Blizzard II in Cyan": 0,
        "Stone in Yellow": 1,
        "Stone II in Yellow": 1,
        "Thunder in Magenta": 2,
        "Thunder II in Magenta": 2,
    }
    MOTIF_SKILLS = {
        "Creature Motif", "Pom Motif", "Wing Motif", "Claw Motif", "Maw Motif",
        "Weapon Motif", "Hammer Motif", "Landscape Motif", "Starry Sky Motif",
    }
    CREATURE_MOTIFS = {"Creature Motif", "Pom Motif", "Wing Motif", "Claw Motif", "Maw Motif"}
    WEAPON_MOTIFS = {"Weapon Motif", "Hammer Motif"}
    LANDSCAPE_MOTIFS = {"Landscape Motif", "Starry Sky Motif"}
    WATER_SPELLS = {"Water in Blue", "Water II in Blue"}
    CYAN_SPELLS = {"Blizzard in Cyan", "Blizzard II in Cyan"}
    YELLOW_SPELLS = {"Stone in Yellow", "Stone II in Yellow"}
    MAGENTA_SPELLS = {"Thunder in Magenta", "Thunder II in Magenta"}

    def __init__(self):
        super().__init__("PCT")
        self.starry_muse_until = -1.0
        # ponytail: level-100 imported axes usually omit pre-pull painting; make this configurable if non-prepull PCT axes matter.
        self.creature_motifs = {"pom"}
        self.weapon_motif_ready = True
        self.landscape_motif_ready = True
        self.hammer_stacks = 0
        self.hammer_until = -1.0
        self.next_hammer = None
        self.palette_gauge = 0
        self.white_paint = 0
        self.black_paint = 0
        self.subtractive_stacks = 0
        self.aetherhues = 0
        self.aetherhues_until = -1.0
        self.hyperphantasia = 0
        self.hyperphantasia_until = -1.0
        self.rainbow_bright_until = -1.0
        self.subtractive_spectrum_until = -1.0
        self.starstruck_until = -1.0
        self.swiftcast_until = -1.0
        self.depictions = set()
        self.moogle_portrait = False
        self.madeen_portrait = False

    def handles_skill_buff(self, name, skill):
        return self._canonical(name, skill) == "Starry Muse"

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    @staticmethod
    def _active(until, current_time):
        return until > current_time

    def _expire_timed_state(self, current_time):
        if self.aetherhues and not self._active(self.aetherhues_until, current_time):
            self.aetherhues = 0
        if self.hammer_stacks and not self._active(self.hammer_until, current_time):
            self.hammer_stacks = 0
            self.next_hammer = None
        if self.hyperphantasia and not self._active(self.hyperphantasia_until, current_time):
            self.hyperphantasia = 0

    def on_press(self, name, skill, current_time, snapshot_time):
        self._expire_timed_state(current_time)
        canonical = self._canonical(name, skill)
        if canonical in self.CREATURE_MOTIFS and self.creature_motifs:
            self.warn("pct_creature_canvas_occupied", current_time, name,
                      f"{canonical} used while the Creature Canvas was occupied.")
        if canonical in self.WEAPON_MOTIFS and (self.weapon_motif_ready or self.hammer_stacks > 0):
            self.warn("pct_weapon_canvas_occupied", current_time, name,
                      f"{canonical} used before the prior Weapon Canvas/Hammer Time was cleared.")
        if canonical in self.LANDSCAPE_MOTIFS and (
                self.landscape_motif_ready or self._active(self.starry_muse_until, current_time)):
            self.warn("pct_landscape_canvas_occupied", current_time, name,
                      f"{canonical} used before the prior Landscape Canvas/Starry Muse was cleared.")
        required = self.CREATURE_MUSE_REQUIREMENTS.get(canonical)
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
        if canonical in self.HAMMER_CHAIN and self.next_hammer and canonical != self.next_hammer:
            self.warn("pct_hammer_chain_mismatch", current_time, name,
                      f"{canonical} used while the tracked Hammer chain expected {self.next_hammer}.")
        if canonical == "Star Prism" and not self._active(self.starstruck_until, snapshot_time):
            self.warn("pct_starstruck_missing", current_time, name,
                      "Star Prism used without a tracked Starstruck state.")
        if canonical == "Subtractive Palette":
            if self.subtractive_stacks > 0:
                self.warn("pct_subtractive_palette_active", current_time, name,
                          "Subtractive Palette used while its prior stacks were still active.")
            if self.subtractive_spectrum_until <= current_time and self.palette_gauge < 50:
                self.warn("pct_palette_low", current_time, name,
                          f"Subtractive Palette used with Palette Gauge {self.palette_gauge}; expected at least 50.")
        required_hue = self.NORMAL_HUE_REQUIREMENTS.get(canonical)
        if required_hue is not None:
            if self.subtractive_stacks > 0:
                self.warn("pct_subtractive_palette_active", current_time, name,
                          f"{canonical} used while Subtractive Palette was active.")
            if self.aetherhues != required_hue:
                self.warn("pct_aetherhues_mismatch", current_time, name,
                          f"{canonical} used with Aetherhues {self.aetherhues}; expected {required_hue}.")
        required_hue = self.SUBTRACTIVE_HUE_REQUIREMENTS.get(canonical)
        if required_hue is not None:
            if self.subtractive_stacks <= 0:
                self.warn("pct_subtractive_palette_missing", current_time, name,
                          f"{canonical} used without tracked Subtractive Palette stacks.")
            if self.aetherhues != required_hue:
                self.warn("pct_aetherhues_mismatch", current_time, name,
                          f"{canonical} used with Aetherhues {self.aetherhues}; expected {required_hue}.")
        if canonical == "Holy in White" and self.white_paint <= 0:
            self.warn("pct_white_paint_low", current_time, name,
                      "Holy in White used without tracked White Paint.")
        if canonical == "Holy in White" and self.black_paint > 0:
            self.warn("pct_monochrome_tones_active", current_time, name,
                      "Holy in White used while Monochrome Tones had converted paint to Black Paint.")
        if canonical == "Comet in Black" and self.black_paint <= 0:
            self.warn("pct_black_paint_low", current_time, name,
                      "Comet in Black used without tracked Black Paint.")
        if canonical == "Mog of the Ages" and not self.moogle_portrait:
            self.warn("pct_moogle_portrait_missing", current_time, name,
                      "Mog of the Ages used without a tracked Moogle Portrait.")
        if canonical == "Mog of the Ages" and self.madeen_portrait:
            self.warn("pct_madeen_portrait_active", current_time, name,
                      "Mog of the Ages used while its button should be Retribution of the Madeen.")
        if canonical == "Retribution of the Madeen" and not self.madeen_portrait:
            self.warn("pct_madeen_portrait_missing", current_time, name,
                      "Retribution of the Madeen used without a tracked Madeen Portrait.")
        if canonical != "Swiftcast" and skill.get("cast", 0) and self._active(
                self.swiftcast_until, current_time):
            self.swiftcast_until = -1.0
        return {}

    def on_press_complete(self, name, current_time):
        self._apply_action(self._canonical(name), current_time)

    def on_press_confirmed(self, name, skill, current_time, payload):
        self._apply_action(self._canonical(name, skill), current_time)

    def _consume_hyperphantasia(self, canonical, current_time):
        if canonical not in self.HYPERPHANTASIA_CONSUMERS or self.hyperphantasia <= 0:
            return
        # ponytail: axes have no field-position column, so being inside Starry Muse is assumed while it is active.
        if not self._active(self.hyperphantasia_until, current_time) or not self._active(
                self.starry_muse_until, current_time):
            return
        self.hyperphantasia -= 1
        if self.hyperphantasia == 0:
            self.hyperphantasia_until = -1.0
            self.rainbow_bright_until = current_time + 30.0

    def _apply_action(self, canonical, current_time):
        if canonical == "Starry Muse":
            self.starry_muse_until = current_time + 20.5
            self.subtractive_spectrum_until = current_time + 30.0
            self.starstruck_until = current_time + 20.0
            self.landscape_motif_ready = False
            self.hyperphantasia = 5
            self.hyperphantasia_until = current_time + 30.0
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
            self.hammer_until = current_time + 30.0
            self.next_hammer = "Hammer Stamp"
        elif canonical in {"Hammer Stamp", "Hammer Brush", "Polishing Hammer"}:
            self.hammer_stacks = max(0, self.hammer_stacks - 1)
            self.next_hammer = self.HAMMER_CHAIN[canonical]
            if self.hammer_stacks == 0:
                self.hammer_until = -1.0
        elif canonical == "Pom Muse":
            self.creature_motifs.discard("pom")
            self.depictions.add("pom")
        elif canonical == "Winged Muse":
            self.creature_motifs.discard("wing")
            self.depictions.add("wing")
            if {"pom", "wing"} <= self.depictions:
                self.moogle_portrait = True
        elif canonical == "Clawed Muse":
            self.creature_motifs.discard("claw")
            self.depictions.add("claw")
        elif canonical == "Fanged Muse":
            self.creature_motifs.discard("maw")
            self.depictions.add("maw")
            if {"pom", "wing", "claw", "maw"} <= self.depictions:
                self.madeen_portrait = True
                self.depictions.difference_update({"pom", "wing", "claw", "maw"})
        elif canonical == "Mog of the Ages":
            self.moogle_portrait = False
        elif canonical == "Retribution of the Madeen":
            self.madeen_portrait = False
        elif canonical == "Subtractive Palette":
            if self.subtractive_spectrum_until > current_time:
                self.subtractive_spectrum_until = -1.0
            else:
                self.palette_gauge = max(0, self.palette_gauge - 50)
            self.subtractive_stacks = 3
            if self.white_paint > 0:
                self.white_paint -= 1
                self.black_paint = min(5, self.black_paint + 1)
        elif canonical in {"Fire in Red", "Fire II in Red"}:
            self.aetherhues = 1
            self.aetherhues_until = current_time + 30.0
        elif canonical in {"Aero in Green", "Aero II in Green"}:
            self.aetherhues = 2
            self.aetherhues_until = current_time + 30.0
        elif canonical in self.WATER_SPELLS:
            self.aetherhues = 0
            self.aetherhues_until = -1.0
            self.palette_gauge = min(100, self.palette_gauge + 25)
            self.white_paint = min(5, self.white_paint + 1)
        elif canonical in self.CYAN_SPELLS:
            self.subtractive_stacks = max(0, self.subtractive_stacks - 1)
            self.aetherhues = 1
            self.aetherhues_until = current_time + 30.0
        elif canonical in self.YELLOW_SPELLS:
            self.subtractive_stacks = max(0, self.subtractive_stacks - 1)
            self.aetherhues = 2
            self.aetherhues_until = current_time + 30.0
        elif canonical in self.MAGENTA_SPELLS:
            self.subtractive_stacks = max(0, self.subtractive_stacks - 1)
            self.aetherhues = 0
            self.aetherhues_until = -1.0
            self.white_paint = min(5, self.white_paint + 1)
        elif canonical == "Holy in White":
            self.white_paint = max(0, self.white_paint - 1)
        elif canonical == "Comet in Black":
            self.black_paint = max(0, self.black_paint - 1)
        elif canonical == "Rainbow Drip":
            self.white_paint = min(5, self.white_paint + 1)
            if self.rainbow_bright_until > current_time:
                self.rainbow_bright_until = -1.0
        elif canonical == "Star Prism":
            self.starstruck_until = -1.0
        elif canonical == "Swiftcast":
            self.swiftcast_until = current_time + 10.0
        self._consume_hyperphantasia(canonical, current_time)

    def effective_cast_time(self, name, skill, event, current_time, default_cast_time):
        if event and event.get("cast_time") is not None:
            return default_cast_time
        self._expire_timed_state(current_time)
        canonical = self._canonical(name, skill)
        if current_time < 0 and canonical in self.MOTIF_SKILLS:
            return 0.0
        if canonical == "Rainbow Drip" and self._active(self.rainbow_bright_until, current_time):
            return 0.0
        if default_cast_time > 0 and self._active(self.swiftcast_until, current_time):
            return 0.0
        if (canonical in self.HYPERPHANTASIA_CONSUMERS
                and self.hyperphantasia > 0
                and self._active(self.hyperphantasia_until, current_time)
                and self._active(self.starry_muse_until, current_time)):
            return default_cast_time * 0.75
        return default_cast_time

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
