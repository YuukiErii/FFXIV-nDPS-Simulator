try:
    from .base import JobState
except ImportError:
    from base import JobState


class SamJobState(JobState):
    COMBO_CANONICAL = {
        "晓风": "Gyofu",
        "阵风": "Jinpu",
        "士风": "Shifu",
        "月光": "Gekko",
        "花车": "Kasha",
        "雪风": "Yukikaze",
    }

    def __init__(self):
        super().__init__("SAM")
        self.fugetsu_until = -1.0
        self.shifu_until = -1.0
        self.meikyo_stacks = 0
        self.meikyo_until = -1.0
        self.enhanced_enpi_until = -1.0
        self.combo_action = None
        self.combo_time = -1.0
        self.kenki = 0
        self.sen = set()
        self.meditation_stacks = 0
        self.zanshin_ready = False
        self.kaeshi_ready = set()
        self.meditate_started_at = None
        self.meditate_ticks_applied = 0
        self._pending_canonical = None

    def _canonical(self, name, skill=None):
        return (skill or {}).get("amas_name") or name

    def _combo_canonical(self, name):
        return self.COMBO_CANONICAL.get(name, name)

    def _sync_meditate(self, current_time):
        if self.meditate_started_at is None:
            return
        available_ticks = min(5, max(0, int((current_time - self.meditate_started_at) // 3.0)))
        new_ticks = available_ticks - self.meditate_ticks_applied
        if new_ticks <= 0:
            return
        self.meditation_stacks = min(3, self.meditation_stacks + new_ticks)
        self.kenki = min(100, self.kenki + 10 * new_ticks)
        self.meditate_ticks_applied = available_ticks

    def _warn_if_resource_short(self, canonical, current_time, name):
        kenki_costs = {
            "Hissatsu: Shinten": 10,
            "Hissatsu: Kyuten": 10,
            "Hissatsu: Gyoten": 10,
            "Hissatsu: Yaten": 10,
            "Hissatsu: Senei": 25,
            "Hissatsu: Guren": 25,
        }
        cost = kenki_costs.get(canonical)
        if cost and self.kenki < cost:
            self.warn("sam_kenki_low", current_time, name,
                      f"{canonical} used with Kenki {self.kenki}; expected at least {cost}.")
        if canonical == "Zanshin" and not self.zanshin_ready:
            self.warn("sam_zanshin_not_ready", current_time, name,
                      "Zanshin used without a tracked Ikishoten/Zanshin Ready state.")
        if canonical in {"Higanbana", "Tenka Goken"} and len(self.sen) < 1:
            self.warn("sam_sen_low", current_time, name,
                      f"{canonical} used with {len(self.sen)} Sen; expected at least 1.")
        if canonical in {"Midare Setsugekka", "Tendo Setsugekka"} and len(self.sen) < 3:
            self.warn("sam_sen_low", current_time, name,
                      f"{canonical} used with {len(self.sen)} Sen; expected 3.")
        if canonical in {"Kaeshi: Setsugekka", "Tendo Kaeshi Setsugekka", "Kaeshi: Goken",
                         "Tendo Kaeshi Goken", "Kaeshi: Namikiri"} and canonical not in self.kaeshi_ready:
            self.warn("sam_kaeshi_not_ready", current_time, name,
                      f"{canonical} used without the matching prior Iaijutsu/Ogi action.")
        if canonical in {"Shoha", "Shoha II"} and self.meditation_stacks < 3:
            self.warn("sam_meditation_low", current_time, name,
                      f"{canonical} used with Meditation stacks {self.meditation_stacks}; expected 3.")

    def on_press(self, name, skill, current_time, snapshot_time):
        canonical = self._canonical(name, skill)
        self._sync_meditate(current_time)
        if canonical not in {"Meditate", "默想"}:
            self.meditate_started_at = None
        self._pending_canonical = canonical
        self._warn_if_resource_short(canonical, current_time, name)

        if name == "必杀剑·夜天":
            self.enhanced_enpi_until = current_time + 15.0

        enhanced_enpi = False
        if name == "燕飞" and self.enhanced_enpi_until > snapshot_time:
            enhanced_enpi = True
            self.enhanced_enpi_until = -1.0
        return {"enhanced": enhanced_enpi}

    def on_press_complete(self, name, current_time):
        canonical = self._pending_canonical or name
        self._pending_canonical = None
        if canonical in {"Meikyo Shisui", "明镜止水"}:
            self.meikyo_stacks = 3
            self.meikyo_until = current_time + 20.0
        elif canonical in {"Meditate", "默想"}:
            self.meditate_started_at = current_time + 0.62
            self.meditate_ticks_applied = 0

        if canonical in {"Higanbana", "Tenka Goken", "Tendo Goken", "Midare Setsugekka",
                         "Tendo Setsugekka", "Ogi Namikiri"}:
            self.meditation_stacks = min(3, self.meditation_stacks + 1)
        if canonical == "Tenka Goken":
            self.kaeshi_ready.add("Kaeshi: Goken")
        elif canonical == "Tendo Goken":
            self.kaeshi_ready.add("Tendo Kaeshi Goken")
        elif canonical == "Midare Setsugekka":
            self.kaeshi_ready.add("Kaeshi: Setsugekka")
        elif canonical == "Tendo Setsugekka":
            self.kaeshi_ready.add("Tendo Kaeshi Setsugekka")
        elif canonical == "Ogi Namikiri":
            self.kaeshi_ready.add("Kaeshi: Namikiri")

    def consume_combo_override(self, name, skill, current_time):
        if self.meikyo_stacks <= 0 or self.meikyo_until <= current_time:
            return False
        if skill.get("combo_prev") or name in ["雪风", "月光", "花车", "晓风"]:
            self.meikyo_stacks -= 1
            return True
        return False

    def is_combo(self, name, skill, current_time, payload):
        if payload.get("meikyo"):
            return True
        combo_prev = skill.get("combo_prev")
        if not combo_prev:
            return False
        expected_actions = {self._combo_canonical(action) for action in combo_prev}
        return self._combo_canonical(self.combo_action) in expected_actions and (current_time - self.combo_time < 30)

    def resolve_potency(self, name, skill, current_time, payload):
        is_combo = self.is_combo(name, skill, current_time, payload)
        potency = skill.get("potency", 0)
        if name == "燕飞" and payload.get("enhanced"):
            potency = skill.get("enhanced_potency", 270)
        elif "base_potency" in skill and not is_combo:
            potency = skill["base_potency"]
        return potency, is_combo

    def on_damage_resolved(self, name, skill, current_time, is_combo, payload):
        canonical = self._canonical(name, skill)
        grant = None
        if is_combo and skill.get("grants"):
            grant = skill["grants"]
        if payload.get("meikyo") and skill.get("meikyo_grants"):
            grant = skill["meikyo_grants"]
        if grant == "fugetsu":
            self.fugetsu_until = current_time + 40.0
        elif grant == "shifu":
            self.shifu_until = current_time + 40.0

        if skill.get("combo_prev") or canonical in {"Gyofu", "Hakaze", "晓风"} or name == "晓风":
            if canonical in {"Gyofu", "Hakaze", "晓风"} or name == "晓风":
                self.combo_action = self._combo_canonical(canonical)
            elif is_combo and canonical in {"Jinpu", "阵风"}:
                self.combo_action = self._combo_canonical(canonical)
            elif is_combo and canonical in {"Shifu", "士风"}:
                self.combo_action = self._combo_canonical(canonical)
            elif is_combo:
                self.combo_action = None
            self.combo_time = current_time

        if canonical in {"Gyofu", "Hakaze"}:
            self.kenki = min(100, self.kenki + 5)
        elif canonical in {"Jinpu", "Shifu"} and is_combo:
            self.kenki = min(100, self.kenki + 5)
        elif canonical == "Yukikaze" and is_combo:
            self.kenki = min(100, self.kenki + 10)
            self.sen.add("setsu")
        elif canonical == "Gekko" and is_combo:
            self.kenki = min(100, self.kenki + 10)
            self.sen.add("getsu")
        elif canonical == "Kasha" and is_combo:
            self.kenki = min(100, self.kenki + 10)
            self.sen.add("ka")
        elif canonical == "Ikishoten":
            self.kenki = min(100, self.kenki + 50)
            self.zanshin_ready = True

        kenki_costs = {
            "Hissatsu: Shinten": 10,
            "Hissatsu: Kyuten": 10,
            "Hissatsu: Gyoten": 10,
            "Hissatsu: Yaten": 10,
            "Hissatsu: Senei": 25,
            "Hissatsu: Guren": 25,
        }
        if canonical in kenki_costs:
            self.kenki = max(0, self.kenki - kenki_costs[canonical])

        if canonical in {"Higanbana", "Tenka Goken", "Tendo Goken"} and self.sen:
            self.sen.clear()
        elif canonical == "Midare Setsugekka":
            self.sen.clear()
        elif canonical == "Tendo Setsugekka":
            self.sen.clear()
        elif canonical in {"Kaeshi: Setsugekka", "Tendo Kaeshi Setsugekka", "Kaeshi: Goken",
                           "Tendo Kaeshi Goken", "Kaeshi: Namikiri"}:
            self.kaeshi_ready.discard(canonical)
        elif canonical in {"Shoha", "Shoha II"}:
            self.meditation_stacks = max(0, self.meditation_stacks - 3)
        elif canonical == "Zanshin":
            self.zanshin_ready = False

    def active_damage_buffs(self, t, target_id=None):
        is_fugetsu = self.fugetsu_until > t
        return {
            "sam_fugetsu": is_fugetsu,
            "damage_mult": 1.13 if is_fugetsu else 1.0,
        }

    def auto_attack_interval_multiplier(self, t):
        return 0.87 if self.shifu_until > t else 1.0

    def format_buffs(self, active_buffs, has_potion=False):
        labels = []
        if active_buffs.get("sam_fugetsu") or active_buffs.get("fugetsu"):
            labels.append("风月")
        if has_potion:
            labels.append("药")
        return labels
