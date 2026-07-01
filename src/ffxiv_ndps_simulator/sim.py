import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import argparse
import math
import random
import statistics
import csv
import threading
import heapq
import ctypes
from collections import deque, Counter, defaultdict
from functools import lru_cache
import os
import sys
import json
from itertools import count
from datetime import datetime

try:
    from xiv_job_data import DEFAULT_MAIN_STATS, DEFAULT_WEAPON_DELAYS, DPS_JOB_ORDER, JOB_PROFILES
    from xiv_skill_provider import get_amas_provider
    from xiv_axis_csv import AxisCsvError, parse_axis_csv, timeline_entry, timeline_time, timeline_targets
    from xiv_sim_core import SimEventType, is_time_in_windows, parse_downtime_windows, parse_marker_track_downtime_windows, push_sim_event, total_window_overlap
    from jobs import MODELED_FOLLOWUP_SKILLS, MODELED_JOB_STATE_SKILLS, create_job_state
except ImportError:
    from .xiv_job_data import DEFAULT_MAIN_STATS, DEFAULT_WEAPON_DELAYS, DPS_JOB_ORDER, JOB_PROFILES
    from .xiv_skill_provider import get_amas_provider
    from .xiv_axis_csv import AxisCsvError, parse_axis_csv, timeline_entry, timeline_time, timeline_targets
    from .xiv_sim_core import SimEventType, is_time_in_windows, parse_downtime_windows, parse_marker_track_downtime_windows, push_sim_event, total_window_overlap
    from .jobs import MODELED_FOLLOWUP_SKILLS, MODELED_JOB_STATE_SKILLS, create_job_state

# 尝试导入 matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def runtime_root():
    """Return the repo root in source runs and the extraction root in PyInstaller runs."""
    try:
        return sys._MEIPASS
    except Exception:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(relative_path):
    """ 获取资源绝对路径，适配 PyInstaller 打包后的临时目录 """
    base_path = runtime_root()
    path = os.path.join(base_path, relative_path)
    if os.path.exists(path):
        return path
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    if os.path.exists(local_path):
        return local_path
    return path


# ==========================================
# 1. 全局配置与技能库
# ==========================================
AA_POTENCY = 90
AA_DELAY = 0.53
TINCTURE_STR = 432
TINCTURE_DELAY = 0.64
SLIDECAST_WINDOW = 0.5  # 滑步窗口时间
APP_TITLE = "FFXIV Personal nDPS Simulator"
APP_ID = "hyxz.ffxiv.ndps.sim"
PERSONAL_NDPS_DEFINITION = (
    "个人 nDPS/RD: 只统计本职业归属的技能、DoT、普攻、宠物/召唤物和自身增益；"
    "当前 MVP 不扣除外部团辅收益，也不把团辅贡献分摊给队友。"
)

SKILL_DB = {
    "晓风": {"cast": 0, "delay": 0.85, "potency": 240, "base_potency": 240},
    "燕飞": {"cast": 0, "delay": 0.71, "potency": 100, "base_potency": 100},
    "阵风": {"cast": 0, "delay": 0.62, "potency": 300, "base_potency": 140, "combo_prev": ["晓风"],
             "grants": "fugetsu"},
    "士风": {"cast": 0, "delay": 0.80, "potency": 300, "base_potency": 140, "combo_prev": ["晓风"], "grants": "shifu"},
    "月光": {"cast": 0, "delay": 0.76, "potency": 420, "base_potency": 210, "combo_prev": ["阵风"],
             "meikyo_grants": "fugetsu"},
    "花车": {"cast": 0, "delay": 0.62, "potency": 420, "base_potency": 210, "combo_prev": ["士风"],
             "meikyo_grants": "shifu"},
    "雪风": {"cast": 0, "delay": 0.85, "potency": 340, "base_potency": 160, "combo_prev": ["晓风"]},
    "彼岸花": {"cast": 1.3, "delay": 0.62, "potency": 200, "dot_potency": 50, "dot_duration": 60},
    "纷乱雪月花": {"cast": 1.3, "delay": 0.62, "potency": 680, "guaranteed_crit": True},
    "回返雪月花": {"cast": 0, "delay": 0.62, "potency": 680, "guaranteed_crit": True},
    "天道雪月花": {"cast": 1.3, "delay": 1.03, "potency": 1100, "guaranteed_crit": True},
    "天道回返雪月花": {"cast": 0, "delay": 1.03, "potency": 1100, "guaranteed_crit": True},
    # AOE 技能
    "奥义斩浪": {"cast": 1.3, "delay": 0.49, "potency": 1000, "guaranteed_crit": True, "is_aoe": True, "decay": 0.4},
    "回返斩浪": {"cast": 0, "delay": 0.49, "potency": 1000, "guaranteed_crit": True, "is_aoe": True, "decay": 0.4},
    "必杀剑·震天": {"cast": 0, "delay": 0.62, "potency": 250},
    "必杀剑·晓天": {"cast": 0, "delay": 0.49, "potency": 100},
    "必杀剑·夜天": {"cast": 0, "delay": 0.45, "potency": 100},
    "必杀剑·闪影": {"cast": 0, "delay": 0.67, "potency": 800},
    "必杀剑·九天": {"cast": 0, "delay": 0.62, "potency": 100, "is_aoe": True, "decay": 0},
    "必杀剑·红莲": {"cast": 0, "delay": 0.62, "potency": 400, "is_aoe": True, "decay": 0},
    "天下五剑": {"cast": 1.3, "delay": 0.62, "potency": 300, "is_aoe": True, "decay": 0},
    "回返五剑": {"cast": 0, "delay": 0.62, "potency": 300, "is_aoe": True, "decay": 0},
    "天道五剑": {"cast": 1.3, "delay": 0.62, "potency": 410, "is_aoe": True, "decay": 0},
    "天道回返五剑": {"cast": 0, "delay": 0.62, "potency": 410, "is_aoe": True, "decay": 0},
    "照破": {"cast": 0, "delay": 0.58, "potency": 640, "is_aoe": True, "decay": 0.4},
    "残心": {"cast": 0, "delay": 1.03, "potency": 940, "is_aoe": True, "decay": 0.4},
    "明镜止水": {"cast": 0, "delay": 0, "potency": 0},
    "意气冲天": {"cast": 0, "delay": 0, "potency": 0},
    "爆发药": {"cast": 0, "delay": 0, "potency": 0},
    "风光": {"cast": 0, "delay": 0.76, "potency": 100, "is_aoe": True, "decay": 0},
    "樱花": {"cast": 0, "delay": 0.62, "potency": 120, "is_aoe": True, "decay": 0},
    "满月": {"cast": 0, "delay": 0.62, "potency": 120, "is_aoe": True, "decay": 0},
}

SKILL_TRANSLATION = {
    'Hakaze': '晓风', 'Gyofu': '晓风', 'Jinpu': '阵风', 'Shifu': '士风',
    'Gekko': '月光', 'Kasha': '花车', 'Yukikaze': '雪风',
    'Fuga': '风雅', 'Fuko': '风光', 'Mangetsu': '满月', 'Oka': '樱花', 'Enpi': '燕飞',
    'Higanbana': '彼岸花', 'Tenka Goken': '天下五剑',
    'Midare Setsugekka': '纷乱雪月花', 'Ogi Namikiri': '奥义斩浪',
    'Kaeshi: Setsugekka': '回返雪月花', 'Kaeshi: Namikiri': '回返斩浪',
    'Kaeshi: Goken': '回返五剑', 'Kaeshi: Higanbana': '回返彼岸花',
    'Shoha': '照破', 'Shoha II': '照破二', 'Meikyo Shisui': '明镜止水',
    'Hissatsu: Shinten': '必杀剑·震天', 'Hissatsu: Gyoten': '必杀剑·晓天',
    'Hissatsu: Yaten': '必杀剑·夜天', 'Hissatsu: Senei': '必杀剑·闪影',
    'Hissatsu: Guren': '必杀剑·红莲', 'Hissatsu: Kyuten': '必杀剑·九天',
    'Ikishoten': '意气冲天', 'Zanshin': '残心', 'Hagakure': '叶隐', 'Meditate': '默想',
    'Tendo Setsugekka': '天道雪月花', 'Tendo Kaeshi Setsugekka': '天道回返雪月花',
    'Tendo Goken': '天道五剑', 'Tendo Kaeshi Goken': '天道回返五剑',
    "Tincture": "爆发药", "Grade 4 Gemdraught of Strength": "爆发药",
    "Third Eye": "心眼", "Tengentsu": "天眼通", "Feint": "牵制",
    "True North": "真北", "Arms Length": "亲疏自行", "Second Wind": "内丹",
    "Pop Tengentsu": "天眼通生效"
}

REVERSE_SKILL_TRANSLATION = {v: k for k, v in SKILL_TRANSLATION.items()}
GENERAL_CN_TO_EN = {}
try:
    with open(resource_path(os.path.join("data", "ff14_job_skill_en_cn_map.json")), "r", encoding="utf-8") as f:
        GENERAL_CN_TO_EN = json.load(f).get("cn_to_en", {})
except Exception:
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ff14_job_skill_en_cn_map.json"),
                  "r", encoding="utf-8") as f:
            GENERAL_CN_TO_EN = json.load(f).get("cn_to_en", {})
    except Exception:
        GENERAL_CN_TO_EN = {}


def normalize_skill_name_for_job(name, job):
    if job == "SAM":
        return SKILL_TRANSLATION.get(name, name)
    return name


def translate_to_amas_name(name):
    return REVERSE_SKILL_TRANSLATION.get(name, GENERAL_CN_TO_EN.get(name, name))


def _match_key(name):
    return "".join(ch.lower() for ch in str(name or "") if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


COMMON_SKILL_ALIASES = {
    "Arm's Length": "Arms Length",
    "Fire 3": "Fire III",
    "Fire 4": "Fire IV",
    "Blizzard 3": "Blizzard III",
    "Blizzard 4": "Blizzard IV",
    "Thunder 3": "Thunder III",
    "Thunder 4": "Thunder IV",
    "High Thunder 2": "High Thunder II",
    "Bootshine": "Leaping Opo",
    "True Strike": "Rising Raptor",
    "Snap Punch": "Pouncing Coeurl",
    "Arm of the Destroyer": "Shadow of the Destroyer",
    "Elixir Field": "Elixir Burst",
    "Flint Strike": "Rising Phoenix",
    "Tornado Kick": "Phantom Rush",
    "Masterful Blitz": "Phantom Rush",
    "Dread Fangs": "Reaving Fangs",
    "Fester": "Necrotize",
    "Queen Overdrive": "Automaton Queen",
    "Grade 4 Gemdraught of Strength": "Tincture",
    "Grade 4 Gemdraught of Dexterity": "Tincture",
    "Grade 4 Gemdraught of Intelligence": "Tincture",
}

GENERIC_ZERO_SKILL_REASONS = {
    "Sprint": "通用移动技能，当前不进入伤害统计。",
    "疾跑": "通用移动技能，当前不进入伤害统计。",
    "Arms Length": "通用防击退技能，当前不进入伤害统计。",
    "Arm's Length": "通用防击退技能，当前不进入伤害统计。",
    "Feint": "通用减伤技能，当前不进入伤害统计。",
    "Addle": "通用减伤技能，当前不进入伤害统计。",
    "Lucid Dreaming": "通用回蓝技能，当前不进入伤害统计。",
    "Second Wind": "通用自疗技能，当前不进入伤害统计。",
    "True North": "通用身位辅助技能，当前不进入伤害统计。",
    "Swiftcast": "通用即刻状态，当前只按 CSV castTime 解释。",
    "Surecast": "通用防击退技能，当前不进入伤害统计。",
    "Tincture": "爆发药自身无直接伤害，但会影响后续伤害。",
    "Dualcast": "赤魔连续咏唱状态，当前只按 CSV castTime 解释。",
    "Hyperphantasia": "绘灵超幻状态标记，当前由具体技能轴解释。",
    "Grade 4 Gemdraught of Strength": "爆发药自身无直接伤害，但会影响后续伤害。",
    "Grade 4 Gemdraught of Dexterity": "爆发药自身无直接伤害，但会影响后续伤害。",
    "Grade 4 Gemdraught of Intelligence": "爆发药自身无直接伤害，但会影响后续伤害。",
    "爆发药": "爆发药自身无直接伤害，但会影响后续伤害。",
    "Meditate": "武士资源/状态技能，当前不进入伤害统计。",
    "默想": "武士资源/状态技能，当前不进入伤害统计。",
    "Toggle buff: Meditate": "排轴中的武士默想结束标记，当前不进入伤害统计。",
    "Pop Tengentsu": "武士状态触发标记，当前不进入伤害统计。",
    "天眼通生效": "武士状态触发标记，当前不进入伤害统计。",
    "+10 Soul Gauge": "排轴资源标记，当前不进入伤害统计。",
    "Regress": "钐镰客位移返回技能，当前不进入伤害统计。",
    "Pop Arcane Crest": "钐镰客神秘纹触发标记，当前不进入伤害统计。",
    "Aetherial Manipulation": "黑魔法师位移技能，当前不进入伤害统计。",
    "Between the Lines": "黑魔法师位移技能，当前不进入伤害统计。",
    "Retrace": "黑魔法师位移技能，当前不进入伤害统计。",
}

POTION_KEYS = {_match_key(name) for name in (
    "Tincture",
    "Grade 4 Gemdraught of Strength",
    "Grade 4 Gemdraught of Dexterity",
    "Grade 4 Gemdraught of Intelligence",
    "爆发药",
)}

JOB_STATE_SKILLS = {
    "NIN": {
        "Ten", "Chi", "Jin", "Fuma Shuriken", "Fuma Shuriken (Ten)",
        "Raiton", "Raiton (Chi)", "Suiton", "Suiton (Jin)", "Kassatsu",
        "Bunshin", "Ten Chi Jin", "Meisui", "Dokumori", "Kunai's Bane",
        "Tenri Jindo", "Bhavacakra", "Dream Within a Dream",
        "Phantom Kamaitachi",
    },
    "RPR": {
        "Arcane Circle", "Enshroud", "Soulsow", "Gluttony", "Plentiful Harvest",
        "Sacrificium", "Communio", "Perfectio", "Harvest Moon",
        "+10 Soul Gauge",
    },
    "PCT": {
        "Creature Motif", "Pom Motif", "Wing Motif", "Claw Motif", "Maw Motif",
        "Weapon Motif", "Hammer Motif", "Landscape Motif", "Starry Sky Motif",
        "Pom Muse", "Winged Muse", "Clawed Muse", "Fanged Muse", "Striking Muse",
        "Starry Muse", "Subtractive Palette", "Hyperphantasia", "Rainbow Drip",
        "Hammer Stamp", "Hammer Brush", "Polishing Hammer", "Mog of the Ages",
        "Retribution of the Madeen", "Star Prism",
    },
    "DNC": {
        "Standard Step", "Technical Step", "Standard Finish", "Technical Finish",
        "Flourish", "Devilment", "Fan Dance", "Saber Dance", "Last Dance",
        "Tillana", "Finishing Move",
    },
    "MCH": {
        "Reassemble", "Wildfire", "Hypercharge", "Heat Blast", "Automaton Queen",
        "Queen Overdrive", "Drill", "Air Anchor", "Chain Saw", "Excavator",
    },
    "BRD": {
        "Caustic Bite", "Stormbite", "Iron Jaws", "Mage's Ballad",
        "Army's Paeon", "The Wanderer's Minuet", "Radiant Finale",
        "Battle Voice", "Pitch Perfect", "Sidewinder",
    },
    "BLM": {
        "Fire", "Fire 3", "Fire III", "Fire 4", "Fire IV",
        "Blizzard", "Blizzard 3", "Blizzard III", "Blizzard 4", "Blizzard IV",
        "Paradox", "Despair", "Flare", "Xenoglossy", "Thunder", "High Thunder",
        "High Thunder 2", "High Thunder II", "Ley Lines", "Triplecast", "Swiftcast",
        "Amplifier", "Manafont", "Flare Star", "Transpose", "Umbral Soul",
    },
    "SMN": {
        "Summon Bahamut", "Summon Phoenix", "Summon Solar Bahamut",
        "Summon Ifrit II", "Summon Titan II", "Summon Garuda II",
        "Deathflare", "Akh Morn", "Enkindle Bahamut", "Enkindle Phoenix",
        "Energy Drain", "Fester", "Painflare",
    },
    "RDM": {
        "Dualcast", "Acceleration", "Manafication", "Embolden",
        "Riposte", "Zwerchhau", "Redoublement", "Scorch", "Resolution",
        "Vice of Thorns", "Prefulgence",
    },
}

for _job, _names in MODELED_JOB_STATE_SKILLS.items():
    JOB_STATE_SKILLS.setdefault(_job, set()).update(_names)

FOLLOWUP_RISK_SKILLS = {
    "NIN": {"Bunshin", "Phantom Kamaitachi"},
    "RPR": {"Gluttony", "Enshroud", "Sacrificium", "Communio", "Perfectio"},
    "MCH": {"Automaton Queen", "Queen Overdrive", "Wildfire", "Detonator", "Flamethrower"},
    "SMN": {"Summon Bahamut", "Summon Phoenix", "Summon Solar Bahamut", "Enkindle Bahamut", "Enkindle Phoenix"},
    "PCT": {"Pom Muse", "Winged Muse", "Clawed Muse", "Fanged Muse", "Mog of the Ages", "Retribution of the Madeen"},
}

GENERIC_ZERO_REASON_BY_KEY = {_match_key(name): reason for name, reason in GENERIC_ZERO_SKILL_REASONS.items()}
JOB_STATE_SKILL_KEYS = {
    job: {_match_key(name) for name in names}
    for job, names in JOB_STATE_SKILLS.items()
}
MODELED_JOB_STATE_SKILL_KEYS = {
    job: {_match_key(name) for name in names}
    for job, names in MODELED_JOB_STATE_SKILLS.items()
}
FOLLOWUP_RISK_SKILL_KEYS = {
    job: {_match_key(name) for name in names}
    for job, names in FOLLOWUP_RISK_SKILLS.items()
}
MODELED_FOLLOWUP_SKILL_KEYS = {
    job: {_match_key(name) for name in names}
    for job, names in MODELED_FOLLOWUP_SKILLS.items()
}


@lru_cache(maxsize=4096)
def _skill_lookup_names(name, job=None):
    text = str(name or "").strip()
    candidates = []

    def add(value):
        value = str(value or "").strip()
        if value and value not in candidates:
            candidates.append(value)

    add(text)
    add(COMMON_SKILL_ALIASES.get(text, ""))
    if text.endswith(")") and "(" in text:
        add(text.rsplit("(", 1)[0].strip())
    add(normalize_skill_name_for_job(text, job))
    add(translate_to_amas_name(text))
    for value in list(candidates):
        add(COMMON_SKILL_ALIASES.get(value, ""))
        add(translate_to_amas_name(value))
    return tuple(candidates)


@lru_cache(maxsize=4096)
def _classification_keys(name, job):
    keys = set()
    for value in _skill_lookup_names(name, job):
        key = _match_key(value)
        if key:
            keys.add(key)
    return frozenset(keys)


def _skill_match_candidates(name, job):
    values = {str(name or "").strip()}
    for value in list(values):
        if value:
            values.add(normalize_skill_name_for_job(value, job))
            values.add(translate_to_amas_name(value))
            values.update(_skill_lookup_names(value, job))
    return {_match_key(value) for value in values if _match_key(value)}


def skill_names_match(axis_raw_name, axis_name, log_name, job):
    axis_candidates = _skill_match_candidates(axis_raw_name, job) | _skill_match_candidates(axis_name, job)
    log_candidates = _skill_match_candidates(log_name, job)
    if not axis_candidates or not log_candidates:
        return False
    if axis_candidates & log_candidates:
        return True
    for left in axis_candidates:
        for right in log_candidates:
            if min(len(left), len(right)) >= 4 and (left in right or right in left):
                return True
    return False


def is_potion_skill_name(name, job=None):
    return bool(_classification_keys(name, job) & POTION_KEYS)


class SkillResolver:
    def __init__(self, job="SAM", version="7.5"):
        self.job = job
        self.version = version
        self.provider = get_amas_provider(version=version, level=100)
        self._skill_cache = {}

    def get(self, name):
        cache_key = str(name or "")
        if cache_key in self._skill_cache:
            cached = self._skill_cache[cache_key]
            return dict(cached) if cached is not None else None
        info = None
        if self.provider:
            for lookup_name in _skill_lookup_names(name, self.job):
                amas_name = translate_to_amas_name(lookup_name)
                info = self.provider.get(self.job, amas_name)
                if info:
                    info = dict(info)
                    info['amas_name'] = amas_name
                    if self.job == "SAM":
                        local_name = normalize_skill_name_for_job(lookup_name, self.job)
                        if local_name in SKILL_DB:
                            provider_info = info
                            info = dict(SKILL_DB[local_name])
                            for key in ('amas_name', 'is_gcd', 'damage_class'):
                                if key in provider_info:
                                    info[key] = provider_info[key]
                            if provider_info.get('delay_source') == 'xivintheshell':
                                info['delay'] = provider_info['delay']
                            if 'dot_potency' in info:
                                for key in ('dot_name', 'dot_primary_only'):
                                    if key in provider_info:
                                        info[key] = provider_info[key]
                        info['combo_prev'] = [SKILL_TRANSLATION.get(x, x) for x in info.get('combo_prev', [])]
                        if 'dot_name' in info:
                            info['dot_name'] = SKILL_TRANSLATION.get(info['dot_name'].replace(" (dot)", ""), info['dot_name'])
                    self._skill_cache[cache_key] = info
                    return dict(info)
        if self.job == "SAM":
            for lookup_name in _skill_lookup_names(name, self.job):
                local_name = normalize_skill_name_for_job(lookup_name, self.job)
                if local_name in SKILL_DB:
                    info = dict(SKILL_DB[local_name])
                    self._skill_cache[cache_key] = info
                    return dict(info)
        keys = _classification_keys(name, self.job)
        if keys & (set(GENERIC_ZERO_REASON_BY_KEY) | POTION_KEYS):
            info = {
                "cast": 0,
                "delay": 0,
                "potency": 0,
                "base_potency": 0,
                "combo_prev": [],
                "guaranteed_crit": False,
                "guaranteed_dh": False,
                "is_aoe": False,
                "decay": 0.0,
                "buff": None,
                "damage_class": "",
                "amas_name": translate_to_amas_name(name),
            }
            self._skill_cache[cache_key] = info
            return dict(info)
        self._skill_cache[cache_key] = None
        return None

    def has(self, name):
        return self.get(name) is not None

    def classify_skill(self, name, job=None):
        if job and job != self.job:
            return SkillResolver(job, self.version).classify_skill(name)

        info = self.get(name)
        amas_name = translate_to_amas_name(name)
        keys = _classification_keys(name, self.job)
        needs_state = bool((keys & JOB_STATE_SKILL_KEYS.get(self.job, set())) - MODELED_JOB_STATE_SKILL_KEYS.get(self.job, set()))
        followup_unmodeled = bool((keys & FOLLOWUP_RISK_SKILL_KEYS.get(self.job, set())) - MODELED_FOLLOWUP_SKILL_KEYS.get(self.job, set()))
        zero_reason = next((GENERIC_ZERO_REASON_BY_KEY[k] for k in keys if k in GENERIC_ZERO_REASON_BY_KEY), "")
        if keys & POTION_KEYS:
            zero_reason = zero_reason or "爆发药自身无直接伤害，但会影响后续伤害。"

        if not info:
            resource_marker = str(name or "").strip().startswith("+") and "Gauge" in str(name or "")
            marker_needs_state = resource_marker and not bool(keys & MODELED_JOB_STATE_SKILL_KEYS.get(self.job, set()))
            if zero_reason or resource_marker:
                return {
                    "name": name,
                    "amas_name": amas_name,
                    "recognized": False,
                    "known": True,
                    "category": "zero_damage",
                    "category_label": "0伤害/系统",
                    "does_damage": False,
                    "is_dot": False,
                    "is_aoe": False,
                    "is_buff": bool(keys & POTION_KEYS),
                    "needs_state": needs_state or marker_needs_state,
                    "followup_unmodeled": followup_unmodeled,
                    "reason": zero_reason or "排轴资源标记，当前不进入伤害统计。",
                    "potency": 0,
                    "dot_potency": 0,
                }
            return {
                "name": name,
                "amas_name": amas_name,
                "recognized": False,
                "known": False,
                "category": "unrecognized",
                "category_label": "未识别",
                "does_damage": False,
                "is_dot": False,
                "is_aoe": False,
                "is_buff": False,
                "needs_state": False,
                "followup_unmodeled": False,
                "reason": "技能库和本地别名都没有匹配到。",
                "potency": None,
                "dot_potency": None,
            }

        potency = info.get("potency", 0) or 0
        dot_potency = info.get("dot_potency", 0) or 0
        is_buff = bool(info.get("buff"))
        does_damage = potency > 0 or dot_potency > 0
        is_dot = dot_potency > 0
        is_aoe = bool(info.get("is_aoe"))
        if is_dot:
            category = "dot"
            category_label = "DoT"
        elif is_aoe and does_damage:
            category = "aoe"
            category_label = "AOE伤害"
        elif does_damage:
            category = "damage"
            category_label = "直接伤害"
        else:
            category = "zero_damage"
            category_label = "0伤害/Buff" if is_buff else "0伤害/系统"

        return {
            "name": name,
            "amas_name": amas_name,
            "recognized": True,
            "known": True,
            "category": category,
            "category_label": category_label,
            "does_damage": does_damage,
            "is_dot": is_dot,
            "is_aoe": is_aoe,
            "is_buff": is_buff,
            "needs_state": needs_state,
            "followup_unmodeled": followup_unmodeled,
            "reason": "已由技能库识别。" if not needs_state else "已识别；完整可信模拟还需要职业状态机解释。",
            "potency": potency,
            "dot_potency": dot_potency,
        }


def build_skill_coverage(events, resolver, csv_meta=None):
    csv_meta = csv_meta or {}
    stats = Counter()
    grouped = {}

    for event in events:
        entry = timeline_entry(event)
        name = entry.get("name", "")
        raw_name = entry.get("raw_name", name)
        classification = resolver.classify_skill(name)
        targets = int(entry.get("targets", 1) or 1)
        target_source = entry.get("target_source", "default")
        key = (raw_name, name)

        if key not in grouped:
            grouped[key] = {
                "raw_name": raw_name,
                "name": name,
                "first_time": entry.get("time", 0.0),
                "last_time": entry.get("time", 0.0),
                "count": 0,
                "max_targets": targets,
                "target_sources": set(),
                "classification": classification,
            }
        row = grouped[key]
        row["count"] += 1
        row["last_time"] = entry.get("time", row["last_time"])
        row["max_targets"] = max(row["max_targets"], targets)
        row["target_sources"].add(target_source)

        stats["total_events"] += 1
        if classification["recognized"] or classification["known"]:
            stats["known_events"] += 1
        if classification["category"] == "unrecognized":
            stats["unrecognized_events"] += 1
        elif classification["does_damage"]:
            stats["damage_events"] += 1
        else:
            stats["zero_events"] += 1
        if classification["needs_state"]:
            stats["needs_state_events"] += 1
        if classification["followup_unmodeled"]:
            stats["followup_unmodeled_events"] += 1
        if classification["is_dot"]:
            stats["dot_events"] += 1
        if classification["is_aoe"]:
            stats["aoe_events"] += 1
        if targets > 1:
            stats["multi_target_events"] += 1
        if target_source == "default":
            stats["default_target_events"] += 1

    rows = []
    for row in grouped.values():
        classification = row["classification"]
        target_sources = sorted(row["target_sources"])
        tags = []
        if classification["is_dot"]:
            tags.append("DoT")
        if classification["is_aoe"]:
            tags.append("AOE")
        if classification["is_buff"]:
            tags.append("Buff")
        if classification["needs_state"]:
            tags.append("需要状态机")
        if classification["followup_unmodeled"]:
            tags.append("follow-up待核")
        if "default" in target_sources:
            tags.append("默认目标")
        rows.append({
            **row,
            "target_sources_text": ",".join(target_sources) if target_sources else "-",
            "tags": tags,
            "tags_text": ", ".join(tags) if tags else "-",
        })

    def severity(row):
        cls = row["classification"]
        if cls["category"] == "unrecognized":
            return 0
        if cls["needs_state"] or cls["followup_unmodeled"]:
            return 1
        if "default" in row["target_sources"]:
            return 2
        if cls["category"] == "zero_damage":
            return 3
        return 4

    rows.sort(key=lambda row: (severity(row), row["first_time"], row["name"]))
    stats["unique_skills"] = len(rows)
    stats["recognized_unique"] = sum(1 for row in rows if row["classification"]["recognized"] or row["classification"]["known"])
    stats["unrecognized_unique"] = sum(1 for row in rows if row["classification"]["category"] == "unrecognized")
    stats["needs_state_unique"] = sum(1 for row in rows if row["classification"]["needs_state"])
    stats["followup_unmodeled_unique"] = sum(1 for row in rows if row["classification"]["followup_unmodeled"])

    if stats["unrecognized_events"]:
        status = "不可模拟，存在未识别关键技能"
    elif stats["needs_state_events"] or stats["followup_unmodeled_events"]:
        status = "可跑但结果仅供趋势参考"
    else:
        status = "可模拟"

    return {
        "stats": dict(stats),
        "rows": rows,
        "csv_meta": csv_meta,
        "status": status,
    }


def build_invalid_skill_events(events, resolver, resource_warnings=None):
    rows = []
    for event in events:
        entry = timeline_entry(event)
        name = entry.get("name", "")
        classification = resolver.classify_skill(name)
        category = classification.get("category")
        if category not in {"zero_damage", "unrecognized"}:
            continue
        rows.append({
            "row_no": entry.get("row_no"),
            "time": entry.get("time", 0.0),
            "skill": name,
            "kind": "未识别/不出伤" if category == "unrecognized" else classification.get("category_label", "0伤害"),
            "code": category,
            "source": "import",
            "reason": classification.get("reason", ""),
        })

    for warning in resource_warnings or []:
        if warning.get("code") != "target_untargetable_at_press":
            continue
        rows.append({
            "row_no": warning.get("row_no"),
            "time": warning.get("time", 0.0),
            "skill": warning.get("skill", ""),
            "kind": "上天按不出",
            "code": warning.get("code"),
            "source": "runtime",
            "reason": warning.get("message", ""),
        })

    rows.sort(key=lambda row: (
        float(row.get("time") or 0.0),
        row.get("row_no") if row.get("row_no") is not None else 10**9,
        row.get("skill", ""),
    ))
    return rows


def build_skill_variant_rows(combat_log):
    variants = {}
    for row in combat_log:
        effective = row.get("effective_potency")
        if not isinstance(effective, (int, float)):
            continue
        skill = str(row.get("name", "")).replace(" (Tick)", " (DoT)")
        targets = int(row.get("target_count", row.get("targets", 1)) or 1)
        key = (
            skill,
            targets,
            str(row.get("potency_buffs") or "-"),
            round(float(row.get("base_potency", row.get("potency", 0)) or 0), 6),
            round(float(effective), 6),
            str(row.get("potency_formula") or ""),
        )
        if key not in variants:
            variants[key] = {
                "skill": skill,
                "targets": targets,
                "buffs": key[2],
                "base_potency": key[3],
                "effective_potency": key[4],
                "potency_formula": key[5],
                "count": 0,
                "first_time": float(row.get("time", 0.0) or 0.0),
            }
        variants[key]["count"] += 1
    return sorted(variants.values(), key=lambda row: (row["skill"], row["first_time"], row["targets"]))


def format_coverage_summary(report):
    stats = report.get("stats", {})
    csv_meta = report.get("csv_meta", {})
    lines = [
        f"可信度状态: {report.get('status', '-')}",
        f"CSV 格式: {csv_meta.get('format', '-')} | 技能行: {stats.get('total_events', 0)} | 唯一技能: {stats.get('unique_skills', 0)}",
        f"识别/已知: {stats.get('known_events', 0)} | 未识别: {stats.get('unrecognized_events', 0)} | 0伤害/系统: {stats.get('zero_events', 0)} | 有效伤害: {stats.get('damage_events', 0)}",
        f"DoT: {stats.get('dot_events', 0)} | AOE: {stats.get('aoe_events', 0)} | 多目标: {stats.get('multi_target_events', 0)} | 默认目标数: {stats.get('default_target_events', 0)}",
        f"需要职业状态机: {stats.get('needs_state_events', 0)} | follow-up 待核: {stats.get('followup_unmodeled_events', 0)}",
    ]
    if csv_meta.get("format") == "tts_skillline_csv":
        lines.append("提示: 这是 TTS skillline CSV，已兼容解析；若要完整评估目标数，优先选择排轴网原始 CSV 并导入同名 TXT/JSON。")
    elif stats.get("default_target_events", 0):
        lines.append("提示: 当前有技能使用默认目标数 1；多目标轴建议导入同名 TXT/JSON 目标列表。")
    return "\n".join(lines)


SELF_TEST_BASE_STATS = {
    "main_stat": 6498,
    "crt": 3605,
    "det": 2426,
    "dh": 1793,
    "sks": 689,
    "wd": 158,
    "party_bonus": 1.05,
    "version": "7.5",
}

SELF_TEST_JOB_CSVS = {
    "MNK": os.path.join("examples/skill_lines", "mnk_xivintheshell_smoke", "mnk_xivintheshell_smoke.csv"),
    "DRG": os.path.join("examples/skill_lines", "drg_xivintheshell_smoke", "drg_xivintheshell_smoke.csv"),
    "NIN": os.path.join("examples/skill_lines", "nin_m12s_p2", "nin_830.csv"),
    "SAM": os.path.join("examples/skill_lines", "sam_m9_m12s", "m10s_217.csv"),
    "RPR": os.path.join("examples/skill_lines", "rpr_enuo", "reaper.csv"),
    "VPR": os.path.join("examples/skill_lines", "vpr_xivintheshell_smoke", "vpr_xivintheshell_smoke.csv"),
    "BRD": os.path.join("examples/skill_lines", "brd_xivintheshell_smoke", "brd_xivintheshell_smoke.csv"),
    "MCH": os.path.join("examples/skill_lines", "mch_xivintheshell_smoke", "mch_xivintheshell_smoke.csv"),
    "DNC": os.path.join("examples/skill_lines", "dnc_xivintheshell_smoke", "dnc_xivintheshell_smoke.csv"),
    "BLM": os.path.join("examples/skill_lines", "blm_m10s", "m10s_1b3.csv"),
    "SMN": os.path.join("examples/skill_lines", "smn_xivintheshell_smoke", "smn_xivintheshell_smoke.csv"),
    "RDM": os.path.join("examples/skill_lines", "rdm_xivintheshell_smoke", "rdm_xivintheshell_smoke.csv"),
    "PCT": os.path.join("examples/skill_lines", "pct_fru", "23_desaturation.csv"),
}

SELF_TEST_HISTORICAL_CSVS = {
    "SAM": os.path.join("examples/skill_lines", "sam_m9_m12s", "m10s_217.csv"),
    "NIN": os.path.join("examples/skill_lines", "nin_m12s_p2", "nin_830.csv"),
    "RPR": os.path.join("examples/skill_lines", "rpr_enuo", "reaper.csv"),
    "PCT": os.path.join("examples/skill_lines", "pct_fru", "23_desaturation.csv"),
}

SELF_TEST_RESOURCE_GROUPS = {
    "game.txt": ("game.txt", os.path.join("ffxiv_ndps_simulator", "game.txt")),
    "stat_fns.txt": ("stat_fns.txt", os.path.join("ffxiv_ndps_simulator", "stat_fns.txt")),
    "damage_cal.txt": ("damage_cal.txt", os.path.join("ffxiv_ndps_simulator", "damage_cal.txt")),
    "skill mapping": (os.path.join("data", "ff14_job_skill_en_cn_map.json"),),
    "icon": ("FFXIV_SIM.ico", "XIV_SIM.ico", "ffxiv_ndps.ico", os.path.join("ffxiv_ndps_simulator", "ffxiv_ndps.ico")),
}


def _first_existing_resource(relative_paths):
    for relative_path in relative_paths:
        path = resource_path(relative_path)
        if os.path.exists(path):
            return path
    return None


def _self_test_load_target_actions(csv_path):
    candidates = [os.path.splitext(csv_path)[0] + ".txt", os.path.splitext(csv_path)[0] + ".json"]
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            actions = [item for item in data.get("actions", []) if item.get("type") == "Skill"]
            if actions:
                return candidate, actions
        except Exception:
            continue
    return None, []


def _self_test_attach_target_counts(events, actions, job):
    final = []
    txt_idx = 0
    search_window = 15
    for row in events:
        raw_name = row.get("raw_name", row["name"])
        sim_name = row["name"]
        target_count = 1
        target_source = "default"
        target_ids = []
        if actions:
            for i in range(txt_idx, min(txt_idx + search_window, len(actions))):
                item = actions[i]
                txt_name = item.get("skillName", "")
                if skill_names_match(raw_name, sim_name, txt_name, job):
                    if "targetList" in item:
                        target_count = len(item["targetList"])
                        target_ids = list(item["targetList"])
                    else:
                        target_count = item.get("targetCount", 1)
                        target_ids = []
                    txt_idx = i + 1
                    target_source = "txt"
                    break
        out = dict(row)
        out["targets"] = int(target_count)
        if target_ids:
            out["target_ids"] = target_ids
        out["target_source"] = target_source
        final.append(out)
    return final


def _self_test_run_formula_smoke():
    from xiv_damage_formula import DamageModifiers, FormulaStats, XivDamageFormula

    formula = XivDamageFormula(
        FormulaStats.from_job(
            job="SAM",
            main_stat=6498,
            crit=3605,
            det=2426,
            dh=1793,
            speed=689,
            wd=158,
            weapon_delay=2.64,
            party_bonus=1.05,
        )
    )
    checks = [
        ("crit_rate", formula.crit_rate(), 0.279),
        ("crit_bonus", formula.crit_bonus(), 0.629),
        ("direct_hit_rate", formula.direct_hit_rate(), 0.271),
        ("gcd_job", formula.gcd_seconds()[1], 2.148),
    ]
    for name, actual, expected in checks:
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9):
            raise AssertionError(f"{name}: expected {expected}, got {actual}")
    direct = formula.base_direct_damage(420)
    dot = formula.base_physical_dot_damage(50)
    auto = formula.base_auto_damage(90)
    if direct != 33823 or dot != 4073 or auto != 6448:
        raise AssertionError(f"formula bases changed: direct={direct}, dot={dot}, auto={auto}")
    forced = formula.base_direct_damage(680, DamageModifiers(main_stat_add=432, forced_crit=True, crit_rate_add=0.10))
    if forced != 62042:
        raise AssertionError(f"forced crit base changed: {forced}")
    return {"direct_base_420": direct, "dot_base_50": dot, "auto_base_90": auto}


def _self_test_run_csv(job, relative_path, require_txt=False):
    csv_path = resource_path(relative_path)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"missing sample CSV: {relative_path}")
    events, meta = parse_axis_csv(
        csv_path,
        normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job),
    )
    target_path, actions = _self_test_load_target_actions(csv_path)
    if require_txt and not actions:
        raise AssertionError(f"sample has no usable TXT/JSON target data: {relative_path}")
    events = _self_test_attach_target_counts(events, actions, job)
    if target_path:
        meta = dict(meta)
        meta["target_file"] = target_path

    resolver = SkillResolver(job)
    if resolver.provider is None:
        raise AssertionError("ama_xiv_combat_sim provider is unavailable")
    report = build_skill_coverage(events, resolver, csv_meta=meta)
    stats = report["stats"]
    blocking = (
        stats.get("unrecognized_events", 0),
        stats.get("needs_state_events", 0),
        stats.get("followup_unmodeled_events", 0),
    )
    if any(blocking):
        raise AssertionError(
            f"coverage issue for {relative_path}: unknown={blocking[0]}, "
            f"needs_state={blocking[1]}, followup={blocking[2]}"
        )

    sim_stats = dict(SELF_TEST_BASE_STATS)
    sim_stats["job"] = job
    sim = DpsSimulator(sim_stats, events, iterations=1)
    total, duration, *_ = sim.run_one_simulation(is_first_run=False)
    if duration <= 0 or total <= 0:
        raise AssertionError(f"simulation did not produce positive output for {relative_path}")
    return {
        "rows": len(events),
        "unique": stats.get("unique_skills", 0),
        "duration": duration,
        "total": total,
        "target_source": "txt/json" if target_path else "default",
    }


def run_self_test():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"{APP_TITLE} self-test")
    print(f"runtime_root={runtime_root()}")
    failures = []

    for label, candidates in SELF_TEST_RESOURCE_GROUPS.items():
        path = _first_existing_resource(candidates)
        if path:
            print(f"[OK] resource {label}: {path}")
        else:
            failures.append(f"missing resource {label}: {', '.join(candidates)}")
            print(f"[FAIL] resource {label}")

    if len(JOB_PROFILES) < len(DPS_JOB_ORDER):
        failures.append(f"job profiles incomplete: {len(JOB_PROFILES)}/{len(DPS_JOB_ORDER)}")
        print(f"[FAIL] job profiles incomplete: {len(JOB_PROFILES)}/{len(DPS_JOB_ORDER)}")
    else:
        print(f"[OK] job profiles: {len(JOB_PROFILES)} DPS jobs")

    try:
        formula = _self_test_run_formula_smoke()
        print(
            "[OK] formula smoke: "
            f"direct={formula['direct_base_420']} dot={formula['dot_base_50']} auto={formula['auto_base_90']}"
        )
    except Exception as exc:
        failures.append(f"formula smoke failed: {type(exc).__name__}: {exc}")
        print(f"[FAIL] formula smoke: {type(exc).__name__}: {exc}")

    print("[INFO] running 13-job CSV smoke set")
    for job in DPS_JOB_ORDER:
        relative_path = SELF_TEST_JOB_CSVS.get(job)
        if not relative_path:
            failures.append(f"no smoke sample configured for {job}")
            print(f"[FAIL] {job}: no smoke sample configured")
            continue
        try:
            result = _self_test_run_csv(job, relative_path)
            print(
                f"[OK] {job}: rows={result['rows']} unique={result['unique']} "
                f"duration={result['duration']:.3f}s total={result['total']:.3f} "
                f"targets={result['target_source']}"
            )
        except Exception as exc:
            failures.append(f"{job} smoke failed: {type(exc).__name__}: {exc}")
            print(f"[FAIL] {job}: {type(exc).__name__}: {exc}")

    print("[INFO] running historical target-data samples")
    for job, relative_path in SELF_TEST_HISTORICAL_CSVS.items():
        try:
            result = _self_test_run_csv(job, relative_path, require_txt=True)
            print(
                f"[OK] historical {job}: rows={result['rows']} duration={result['duration']:.3f}s "
                f"total={result['total']:.3f} targets={result['target_source']}"
            )
        except Exception as exc:
            failures.append(f"historical {job} failed: {type(exc).__name__}: {exc}")
            print(f"[FAIL] historical {job}: {type(exc).__name__}: {exc}")

    if failures:
        print("[SELF-TEST FAILED]")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[SELF-TEST PASSED]")
    return 0


# ==========================================
# 2. 模拟核心
# ==========================================
class DpsSimulator:
    def __init__(self, stats, timeline_data, downtime_config=None, dot_config=None,
                 multi_boss_mode=False, global_downtime_list=None, iterations=1000, custom_snaps=None):
        self.stats = dict(stats)
        self.job = self.stats.get('job', 'SAM')
        self.stats.setdefault('delay', DEFAULT_WEAPON_DELAYS.get(self.job, 2.64))
        self.stats['version'] = str(self.stats.get('version', '7.5'))
        stats = self.stats
        self.timeline_data = timeline_data
        self.custom_snaps = custom_snaps if custom_snaps else []
        self.multi_boss_mode = multi_boss_mode
        self.downtime_config = downtime_config if downtime_config else {}
        self.global_downtime_list = global_downtime_list if global_downtime_list else []
        self.dot_config = dot_config if dot_config else {}
        self.iterations = iterations

        self.job_profile = JOB_PROFILES.get(self.job, JOB_PROFILES.get('SAM'))
        self.skill_resolver = SkillResolver(self.job, stats['version'])
        level_mods = self.job_profile.level_modifiers
        self.lvl_main = level_mods.main;
        self.lvl_sub = level_mods.sub;
        self.lvl_div = level_mods.div;
        self.lvl_ap = level_mods.ap
        self.party_bonus = stats.get('party_bonus', self.job_profile.party_bonus)
        self.base_main = stats.get('main_stat', stats.get('str'))
        self.base_str = self.base_main  # 兼容旧 UI 文案
        self.job_mod = self.job_profile.job_mod
        self.trait_damage_multiplier = self.job_profile.trait_damage_multiplier

        self.crit_rate = math.floor(200 * (stats['crt'] - self.lvl_sub) / self.lvl_div + 50) / 1000
        self.crit_dmg = math.floor(200 * (stats['crt'] - self.lvl_sub) / self.lvl_div + 1400) / 1000
        self.dh_rate = math.floor(550 * (stats['dh'] - self.lvl_sub) / self.lvl_div) / 1000
        self.dh_dmg = 1.25
        self.det_mult = math.floor(140 * (stats['det'] - self.lvl_main) / self.lvl_div + 1000) / 1000
        self.spd_mult = math.floor(130 * (stats['sks'] - self.lvl_sub) / self.lvl_div + 1000) / 1000

        wd_job_mod = math.floor(self.lvl_main * self.job_mod / 1000)
        self.f_auto = math.floor((wd_job_mod + stats['wd']) * (stats['delay'] / 3.00))
        self.wd_factor = (stats['wd'] + wd_job_mod) / 100

        self.ap_val_normal = self._calc_ap(False)
        self.ap_val_potion = self._calc_ap(True)

    def _calc_ap(self, has_potion):
        eff_main = math.floor(self.base_main * self.party_bonus)
        if has_potion:
            eff_main += min(TINCTURE_STR, math.floor(eff_main * 0.10))
        return math.floor(self.lvl_ap * (eff_main - self.lvl_main) / self.lvl_main + 100)

    @staticmethod
    def calculate_gcd(sks, job='SAM'):
        lvl_sub = 420;
        lvl_div = 2780
        profile = JOB_PROFILES.get(job, JOB_PROFILES.get('SAM'))
        speed_val = math.floor(130 * (sks - lvl_sub) / lvl_div)
        base_ms = math.floor((1000 - speed_val) * 2500 / 1000)
        job_ms = math.floor(base_ms * profile.gcd_modifier)
        return base_ms / 1000.0, job_ms / 1000.0

    def calculate_damage_val(self, potency, is_auto=False, is_dot=False, active_buffs=None, guaranteed_crit=False,
                             guaranteed_dh=False, has_potion=False, force_no_crit=False, force_no_dh=False,
                             job_mod_override=None):
        if active_buffs is None: active_buffs = {}
        ap_val = self.ap_val_potion if has_potion else self.ap_val_normal
        base = potency * (ap_val / 100.0) * self.det_mult

        base *= active_buffs.get('damage_mult', 1.0)
        wd_factor = self.wd_factor
        if job_mod_override is not None:
            wd_job_mod = math.floor(self.lvl_main * float(job_mod_override) / 1000)
            wd_factor = (self.stats['wd'] + wd_job_mod) / 100
        if is_auto:
            base = base * self.spd_mult * (self.f_auto / 100.0)
        elif is_dot:
            base = base * self.spd_mult * wd_factor
        else:
            base = base * wd_factor
        base *= self.trait_damage_multiplier

        crit_rate = min(1.0, max(0.0, self.crit_rate + active_buffs.get('crit_rate_add', 0.0)))
        dh_rate = min(1.0, max(0.0, self.dh_rate + active_buffs.get('dh_rate_add', 0.0)))
        is_crit = False if force_no_crit else (True if guaranteed_crit else (random.random() < crit_rate))
        is_dh = False if force_no_dh else (True if guaranteed_dh else (random.random() < dh_rate))
        val = base * self.crit_dmg if is_crit else base
        if is_dh: val *= self.dh_dmg
        return val * random.uniform(0.95, 1.05), is_crit, is_dh

    # 判定特定目标是否在指定时间点不可选中
    def is_target_untargetable(self, t, tid):
        if not self.multi_boss_mode: return False
        if tid not in self.downtime_config: return False
        return is_time_in_windows(t, self.downtime_config[tid])

    # 判定全局上天 (用于单Boss模式 或 普攻暂停)
    def is_global_downtime(self, t):
        return is_time_in_windows(t, self.global_downtime_list)

    def get_effective_downtime_total(self, end_time):
        return total_window_overlap(self.global_downtime_list, end_time)

    def get_effective_duration(self, end_time):
        return max(1.0, end_time - self.get_effective_downtime_total(end_time))

    def get_skill(self, name):
        return self.skill_resolver.get(name)

    @staticmethod
    def _target_ids_from_payload(payload):
        raw_ids = (payload or {}).get('target_ids') or []
        if not isinstance(raw_ids, (list, tuple)):
            return []
        target_ids = []
        for raw_id in raw_ids:
            try:
                target_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if target_id > 0 and target_id not in target_ids:
                target_ids.append(target_id)
        return target_ids

    def get_active_damage_buffs(self, buffs, t, job_state=None, target_id=None):
        active = job_state.active_damage_buffs(t, target_id=target_id) if job_state else {}
        damage_mult = active.get('damage_mult', 1.0)
        crit_rate_add = active.get('crit_rate_add', 0.0)
        dh_rate_add = active.get('dh_rate_add', 0.0)
        damage_factors = list(active.get('damage_factors', []))
        for key, buff in buffs.items():
            if not isinstance(buff, dict):
                continue
            if buff.get('until', -1.0) <= t:
                continue
            factor = buff.get('damage_mult', 1.0)
            damage_mult *= factor
            if abs(factor - 1.0) > 1e-9:
                damage_factors.append((buff.get('name') or str(key).removeprefix('buff:'), factor))
            crit_rate_add += buff.get('crit_rate_add', 0.0)
            dh_rate_add += buff.get('dh_rate_add', 0.0)
        active['damage_mult'] = damage_mult
        active['crit_rate_add'] = crit_rate_add
        active['dh_rate_add'] = dh_rate_add
        active['damage_factors'] = damage_factors
        return active

    @staticmethod
    def potency_breakdown(base_potency, resolved_potency, active_buffs, target_count=1,
                          is_aoe=False, decay_rate=0.0, state_label="技能状态"):
        base_potency = float(base_potency or resolved_potency or 0.0)
        resolved_potency = float(resolved_potency or 0.0)
        factors = []
        if base_potency > 0 and abs(resolved_potency - base_potency) > 1e-9:
            factors.append((state_label, resolved_potency / base_potency))
        damage_factors = list(active_buffs.get('damage_factors', []))
        factors.extend(damage_factors)
        known_mult = math.prod(float(factor) for _label, factor in damage_factors) if damage_factors else 1.0
        damage_mult = float(active_buffs.get('damage_mult', 1.0) or 1.0)
        if abs(damage_mult - known_mult) > 1e-9:
            factors.append(("增伤合计", damage_mult / known_mult))
        target_factor = 1.0
        if target_count > 1:
            target_factor = 1.0 + (target_count - 1) * (1.0 - decay_rate if is_aoe else 1.0)
            factors.append((f"{target_count}目标", target_factor))
        effective = base_potency * math.prod(float(factor) for _label, factor in factors)
        expression = f"{base_potency:g}"
        for label, factor in factors:
            expression += f" × {float(factor):g} ({label})"
        potency_buffs = "+".join(label for label, _factor in factors if not label.endswith("目标")) or "-"
        return effective, f"{expression} = {effective:.2f}", potency_buffs

    def effective_cast_time(self, skill, event):
        if event and event.get('cast_time') is not None:
            return max(0.0, float(event.get('cast_time') or 0.0))
        cast = float(skill.get('cast', 0) or 0.0)
        if cast <= 0:
            return 0.0
        time_ms = int(round(cast * 1000))
        speed_term = math.ceil(130 * (self.lvl_sub - self.stats.get('sks', self.lvl_sub)) / self.lvl_div)
        return int(1000 * (math.floor(time_ms * (1000 + speed_term) / 10000) / 100)) / 1000.0

    def run_one_simulation(self, is_first_run=False):
        self.last_dot_details = []
        pq = []
        tie_breaker = count()
        for item in self.timeline_data:
            event = timeline_entry(item)
            push_sim_event(pq, event['time'], SimEventType.PRESS, tie_breaker, event)
        push_sim_event(pq, random.uniform(0.0, 3.0), SimEventType.DOT_TICK, tie_breaker, None)

        last_skill_hit_time = 0.0
        for item in self.timeline_data:
            event = timeline_entry(item)
            name = event['name']
            s = self.get_skill(name)
            if s:
                cast, delay = self.effective_cast_time(s, event), s.get('delay', 0.5)
                confirmation_delay = max(0.0, cast - SLIDECAST_WINDOW) if cast > 0 else 0.0
                hit_time = event['time'] + confirmation_delay + delay
                keys = _classification_keys(name, self.job)
                emits_followup_damage = bool(keys & FOLLOWUP_RISK_SKILL_KEYS.get(self.job, set()))
                if s.get('potency', 0) > 0 or s.get('dot_potency', 0) > 0 or emits_followup_damage:
                    last_skill_hit_time = max(last_skill_hit_time, hit_time)

        run_snapshots = {}  # 用于存储本次运行的快照数据 {time: current_damage}
        cp_time = 30.0
        while cp_time < last_skill_hit_time:
            push_sim_event(pq, cp_time, SimEventType.SNAPSHOT, tie_breaker, {'snap_time': cp_time})
            cp_time += 120.0
        all_custom_snaps = set(self.custom_snaps)
        for ct in all_custom_snaps:
            if 0 < ct <= last_skill_hit_time:
                push_sim_event(pq, ct, SimEventType.SNAPSHOT, tie_breaker, {'snap_time': ct})

        history_snapshots = {}
        ht_time = 2.0
        while ht_time <= last_skill_hit_time:
            push_sim_event(pq, ht_time, SimEventType.HISTORY_TICK, tie_breaker, {'snap_time': ht_time})
            ht_time += 2.0

        current_time = 0.0;
        total_damage = 0.0
        skill_dmg_map = defaultdict(float);
        skill_count_map = Counter()
        skill_crit_map = Counter();
        skill_dh_map = Counter();
        skill_cdh_map = Counter()
        skill_target_sum_map = Counter();
        total_hits_in_run = 0

        buffs = {}
        job_state = create_job_state(self.job, self.stats.get('version', '7.5'))
        active_dots = [];
        casting_state = (-1, -1, -1);
        potion_active_until = float("-inf")
        aa_running = False;
        next_aa_timestamp = 0.0
        job_state.configure_mana_ticks(self.stats.get('time_till_first_mana_tick'))

        # 技能计数移到外面，确保 press 和 damage 共享
        # 但为了避免 press 失败导致计数错乱，我们采用 "尝试计数" 和 "成功计数"
        # 实际上，FF14 中如果读条中断，该技能不算使用。
        # 我们在这里维护一个 "准备按下的计数器" 用来查找 Config
        skill_attempt_counter = Counter()
        combat_log = []
        dot_details = []
        dot_detail_counter = count(1)

        while pq:
            t, _, ev_type, _, payload = heapq.heappop(pq)
            if t > last_skill_hit_time + 0.001: break
            current_time = t
            global_dt = self.is_global_downtime(current_time)

            if ev_type == SimEventType.SNAPSHOT:
                snap_t = payload['snap_time']
                run_snapshots[snap_t] = total_damage
                continue  # 处理完直接进行下一个循环

            if ev_type == SimEventType.HISTORY_TICK:
                snap_t = payload['snap_time']
                history_snapshots[snap_t] = total_damage
                continue

            if ev_type == SimEventType.PRESS:
                name = payload['name'];
                target_count = int(payload.get('targets', 1))
                explicit_target_ids = self._target_ids_from_payload(payload)
                if explicit_target_ids:
                    target_count = max(target_count, len(explicit_target_ids))
                skill = self.get_skill(name)
                if not skill: continue
                job_state.advance_time(current_time)

                # --- 1. 准备工作：计数器与快照时间计算 ---
                current_attempt_idx = skill_attempt_counter[name]
                skill_attempt_counter[name] += 1

                # 计算快照时间 (用于判定此时Boss是否在场)
                # 读条技能看滑步点，瞬发技能看当前
                cast_time = job_state.effective_cast_time(
                    name, skill, payload, current_time, self.effective_cast_time(skill, payload)
                )
                snapshot_time = current_time
                if cast_time > 0:
                    snapshot_time = current_time + cast_time - SLIDECAST_WINDOW
                    if snapshot_time < current_time: snapshot_time = current_time

                # --- 2. 确定 Target ID (智能索敌逻辑) ---
                target_id = explicit_target_ids[0] if explicit_target_ids else 1
                is_manual_target = False

                job_state.set_event_context(payload)
                press_state = job_state.on_press(name, skill, current_time, snapshot_time)

                # (A) 优先读取手动配置
                if self.multi_boss_mode and name in self.dot_config:
                    if current_attempt_idx < len(self.dot_config[name]):
                        target_id = self.dot_config[name][current_attempt_idx]
                        is_manual_target = True  # 标记为手动强制


                # (B) 智能索敌 (仅在多Boss模式且无手动配置时生效)
                if self.multi_boss_mode and not is_manual_target:
                    # 检查 T1 是否在快照点上天
                    t1_away = self.is_target_untargetable(snapshot_time, 1)

                    if t1_away:
                        # 如果 T1 不在，检查 T2 是否在
                        t2_away = self.is_target_untargetable(snapshot_time, 2)
                        if not t2_away:
                            # T1 不在且 T2 在 -> 自动切目标打 T2
                            target_id = 2
                        # else: 两个都不在，保持 target_id=1，后续逻辑会判定为无效
                    # else: T1 在场，保持 target_id=1 (主目标优先)

                is_buff_skill = (skill.get('potency', 0) == 0 and skill.get('dot_potency', 0) == 0)
                is_snapshot_invalid = False
                if not is_buff_skill and not job_state.can_activate_without_target(name, skill):
                    if self.multi_boss_mode:
                        is_snapshot_invalid = self.is_target_untargetable(snapshot_time, target_id)
                    else:
                        is_snapshot_invalid = self.is_global_downtime(snapshot_time)

                if is_snapshot_invalid:
                    job_state.warn(
                        "target_untargetable_at_press",
                        current_time,
                        name,
                        f"{name} pressed while T{target_id} is untargetable at {snapshot_time:.3f}s.",
                    )
                    if is_first_run:
                        combat_log.append({
                            'time': current_time, 'name': name, 'potency': '-',
                            'buffs': 'Interrupted', 'crit': '-', 'dh': '-',
                            'dmg': f'0 (T{target_id}不在场)', 'targets': '-'
                        })
                    continue

                if is_potion_skill_name(name, self.job):
                    job_state.on_press_confirmed(
                        name,
                        skill,
                        current_time,
                        {
                            **payload,
                            **press_state,
                            'tid': target_id,
                            'targets': target_count,
                        },
                    )
                    job_state.on_common_action_confirmed(name, skill, current_time)
                    potion_active_until = current_time + TINCTURE_DELAY + 30.0
                    if is_first_run:
                        combat_log.append(
                            {'time': current_time, 'name': '[爆发药]', 'potency': '-', 'buffs': '(Dur 30s)',
                             'crit': '-', 'dh': '-', 'dmg': '-', 'targets': 1})
                    continue

                snapshot_active_buffs = self.get_active_damage_buffs(
                    buffs,
                    snapshot_time,
                    job_state=job_state,
                    target_id=target_id,
                )

                if (job_state.allows_auto_attacks(self.job_profile)
                        and job_state.allows_auto_attack_at(current_time)
                        and job_state.should_start_auto_attacks(name, skill, current_time)
                        and not aa_running and not global_dt):
                    aa_running = True;
                    next_aa_timestamp = max(0.0, current_time)
                    push_sim_event(pq, next_aa_timestamp, SimEventType.AUTO_ATTACK_CHECK, tie_breaker, {'scheduled_time': next_aa_timestamp})

                skill_buff = skill.get('buff')
                if skill_buff and not skill.get('grants') and not job_state.handles_skill_buff(name, skill):
                    buffs[skill_buff['key']] = {
                        'name': skill_buff.get('name', name),
                        'until': current_time + skill_buff['duration'],
                        'damage_mult': skill_buff.get('damage_mult', 1.0),
                        'crit_rate_add': skill_buff.get('crit_rate_add', 0.0),
                        'dh_rate_add': skill_buff.get('dh_rate_add', 0.0),
                    }
                    if is_first_run and skill.get('potency', 0) == 0:
                        combat_log.append({
                            'time': current_time, 'name': f'[{name}]', 'potency': '-',
                            'buffs': f"(Dur {skill_buff['duration']:.0f}s)",
                            'crit': '-', 'dh': '-', 'dmg': '-', 'targets': 1
                        })

                cast, delay = cast_time, skill.get('delay', 0.5)
                hit_time = snapshot_time + delay
                check_time = current_time

                if cast > 0:
                    check_time = current_time + cast - 0.5
                    casting_state = (current_time, current_time + cast, check_time)
                    if aa_running and next_aa_timestamp > current_time:
                        penalty = cast - 0.5;
                        next_aa_timestamp += penalty
                        push_sim_event(
                            pq,
                            next_aa_timestamp,
                            SimEventType.AUTO_ATTACK_CHECK,
                            tie_breaker,
                            {'scheduled_time': next_aa_timestamp},
                        )

                is_potion = (potion_active_until > check_time >= (potion_active_until - 30.0))
                is_meikyo_proc = job_state.consume_combo_override(name, skill, current_time)

                # 关键：将智能判定后的 target_id 传给 damage 事件
                push_sim_event(pq, hit_time, SimEventType.DAMAGE, tie_breaker, {
                    'name': name,
                    'press_time': current_time,
                    'meikyo': is_meikyo_proc,
                    'has_potion': is_potion,
                    'targets': target_count,
                    'target_ids': explicit_target_ids,
                    'tid': target_id,
                    'row_no': payload.get('row_no'),
                    'is_gcd': payload.get('is_gcd'),
                    'multi_boss_mode': self.multi_boss_mode,
                    'snapshot_active_buffs': snapshot_active_buffs,
                    **press_state,
                })

                confirmation_payload = {
                    **payload,
                    **press_state,
                    'name': name,
                    'meikyo': is_meikyo_proc,
                    'tid': target_id,
                    'targets': target_count,
                    'target_ids': explicit_target_ids,
                    'multi_boss_mode': self.multi_boss_mode,
                }
                if cast > 0 and job_state.confirms_at_snapshot(name, skill):
                    push_sim_event(
                        pq, snapshot_time, SimEventType.CONFIRM, tie_breaker, confirmation_payload
                    )
                else:
                    job_state.on_press_confirmed(name, skill, current_time, confirmation_payload)
                    job_state.on_common_action_confirmed(name, skill, current_time)

            elif ev_type == SimEventType.CONFIRM:
                name = payload['name']
                skill = self.get_skill(name)
                job_state.set_event_context(payload)
                job_state.on_press_confirmed(name, skill, current_time, payload)
                job_state.on_common_action_confirmed(name, skill, current_time)

            elif ev_type == SimEventType.DAMAGE:
                name = payload['name'];
                has_potion = payload['has_potion'];
                target_count = payload['targets']
                target_id = payload['tid']  # 从 press 传过来

                skill = self.get_skill(name)
                job_state.set_event_context(payload)
                if not job_state.should_resolve_damage(name, skill, current_time, payload):
                    continue
                skill_count_map[name] += 1

                # --- 核心判定：出伤时刻是否上天 ---
                # 即使快照判定通过了，出伤时如果 Boss 上天，伤害为 0 (免疫)
                is_damage_immune = False

                is_buff_skill = (skill.get('potency', 0) == 0 and skill.get('dot_potency', 0) == 0)

                if not is_buff_skill:
                    if self.multi_boss_mode:
                        # 注意：这里会自动调用修改后的开区间函数
                        if self.is_target_untargetable(current_time, target_id):
                            is_damage_immune = True
                    else:
                        if self.is_global_downtime(current_time):
                            is_damage_immune = True

                # 只有伤害有效时，才计入击中数 (便于统计)
                if not is_damage_immune:
                    skill_target_sum_map[name] += target_count
                    total_hits_in_run += 1

                step_total_damage = 0;
                main_crit = False;
                main_dh = False
                crit_count = 0

                active_buffs = payload.get('snapshot_active_buffs')
                if active_buffs is None:
                    active_buffs = self.get_active_damage_buffs(
                        buffs,
                        current_time,
                        job_state=job_state,
                        target_id=target_id,
                    )
                potency, is_combo = job_state.resolve_potency(name, skill, current_time, payload)
                is_aoe_skill = skill.get('is_aoe', False);
                decay_rate = skill.get('decay', 0.0)
                payload['damage_immune'] = is_damage_immune

                # 如果没上天，计算伤害
                if not is_damage_immune:
                    for i in range(target_count):
                        modifier = 1.0
                        if is_aoe_skill and i > 0: modifier = 1.0 - decay_rate
                        dmg_val, is_c, is_d = self.calculate_damage_val(potency, is_auto=False,
                                                                        active_buffs=active_buffs,
                                                                        guaranteed_crit=(
                                                                            skill.get('guaranteed_crit', False)
                                                                            or payload.get('guaranteed_crit', False)
                                                                        ),
                                                                        guaranteed_dh=(
                                                                            skill.get('guaranteed_dh', False)
                                                                            or payload.get('guaranteed_dh', False)
                                                                        ),
                                                                        has_potion=has_potion,
                                                                        force_no_crit=payload.get('force_no_crit', False),
                                                                        force_no_dh=payload.get('force_no_dh', False),
                                                                        job_mod_override=skill.get('job_mod_override'))
                        step_total_damage += (dmg_val * modifier)
                        if is_c: crit_count += 1
                        if i == 0: main_crit = is_c; main_dh = is_d

                # 如果上天了，step_total_damage 为 0



                total_damage += step_total_damage
                skill_dmg_map[name] += step_total_damage
                if main_crit: skill_crit_map[name] += 1
                if main_dh: skill_dh_map[name] += 1
                if main_crit and main_dh: skill_cdh_map[name] += 1
                payload['source_roll_available'] = bool(potency > 0 and not is_damage_immune)
                payload['source_crit'] = main_crit
                payload['source_crit_count'] = crit_count
                payload['source_dh'] = main_dh

                # --- DoT 挂载 ---
                # 只要进入了 damage 阶段（说明 press 阶段快照判定通过了）
                # 即使当前出伤是 0 (免疫)，DoT 依然会挂在目标身上
                # 之后的 tick 事件会负责判断每一跳是否有伤害
                for dot_application in job_state.dot_applications(
                        name, skill, current_time, target_count, target_id, active_buffs, has_potion):
                    dot_application = dict(dot_application)
                    dot_key = dot_application.get('dot_key', dot_application.get('source_name', dot_application['name']))
                    target_aware_dot = self.multi_boss_mode or bool(payload.get('target_ids'))
                    if target_aware_dot:
                        dot_application['target_explicit'] = bool(payload.get('target_ids'))
                        active_dots = [
                            d for d in active_dots
                            if not (d.get('dot_key', d.get('source_name', d['name'])) == dot_key
                                    and d['tid'] == dot_application.get('tid', target_id))
                        ]
                    else:
                        active_dots = [
                            d for d in active_dots
                            if d.get('dot_key', d.get('source_name', d['name'])) != dot_key
                        ]
                    if is_first_run:
                        b_list = job_state.format_buffs(dot_application.get('buffs', {}), dot_application.get('has_potion', False))
                        detail = {
                            'dot_id': next(dot_detail_counter),
                            'apply_time': current_time,
                            'source_name': dot_application.get('source_name') or name,
                            'name': dot_application.get('name', name),
                            'target_id': dot_application.get('tid', target_id),
                            'targets': int(dot_application.get('targets', 1) or 1),
                            'potency': dot_application.get('potency', 0),
                            'expire_time': dot_application.get('expire', current_time),
                            'buffs_text': "+".join(b_list) if b_list else "-",
                            'has_potion': bool(dot_application.get('has_potion', False)),
                            'tick_events': 0,
                            'ticks': 0,
                            'missed_tick_events': 0,
                            'missed_ticks': 0,
                            'damage': 0.0,
                            'crit_ticks': 0,
                            'dh_ticks': 0,
                            'last_tick_time': None,
                            'row_no': payload.get('row_no'),
                        }
                        dot_application['detail'] = detail
                        dot_details.append(detail)
                    active_dots.append(dot_application)

                if is_first_run and potency > 0:
                    b_list = job_state.format_buffs(active_buffs, has_potion)
                    base_potency = skill.get('potency', potency)
                    state_label = "技能状态"
                    if self.job == "BLM":
                        af = active_buffs.get("blm_astral_fire", 0)
                        ui = active_buffs.get("blm_umbral_ice", 0)
                        state_label = f"星火{af}" if af else (f"灵冰{ui}" if ui else state_label)
                    effective_potency, potency_formula, potency_buffs = self.potency_breakdown(
                        base_potency,
                        potency,
                        active_buffs,
                        target_count,
                        is_aoe_skill,
                        decay_rate,
                        state_label,
                    )

                    dmg_str = f"{step_total_damage:,.0f}"
                    if is_damage_immune: dmg_str += " (免疫)"

                    if potency > 0:
                        c_str = "✔" if main_crit else ""
                        d_str = "✔" if main_dh else ""
                    else:
                        c_str = "-"
                        d_str = "-"

                    combat_log.append({
                        'time': current_time, 'name': name, 'potency': potency,
                        'base_potency': base_potency,
                        'effective_potency': effective_potency,
                        'potency_formula': potency_formula,
                        'potency_buffs': potency_buffs,
                        'buffs': "+".join(b_list) if b_list else "-",
                        'crit': c_str, 'dh': d_str,
                        'dmg': dmg_str, 'targets': target_count, 'target_count': target_count,
                    })

                job_state.on_damage_resolved(name, skill, current_time, is_combo, payload)
                for followup in job_state.followup_damage_events(name, skill, current_time, payload):
                    followup_payload = {
                        'source': name,
                        'tid': target_id,
                        'targets': target_count,
                        'has_potion': has_potion,
                    }
                    followup_payload.update(followup)
                    if followup_payload.get('snapshot_potion_now'):
                        followup_payload['has_potion'] = (
                            potion_active_until > current_time >= (potion_active_until - 30.0)
                        )
                    followup_time = current_time + float(followup_payload.get('delay', 0.0) or 0.0)
                    if followup_payload.get('extends_duration', True):
                        last_skill_hit_time = max(last_skill_hit_time, followup_time)
                    push_sim_event(
                        pq,
                        followup_time,
                        SimEventType.FOLLOWUP_DAMAGE,
                        tie_breaker,
                        followup_payload,
                    )

            elif ev_type == SimEventType.FOLLOWUP_DAMAGE:
                if not job_state.is_followup_active(payload, current_time):
                    continue
                name = payload['name']
                potency = payload.get('potency', 0) or 0
                target_count = int(payload.get('targets', 1))
                target_id = payload.get('tid', 1)
                has_potion = payload.get('has_potion', False)
                if payload.get('snapshot_potion_at_followup'):
                    has_potion = potion_active_until > current_time >= (potion_active_until - 30.0)
                is_damage_immune = False
                if self.multi_boss_mode:
                    if self.is_target_untargetable(current_time, target_id):
                        is_damage_immune = True
                else:
                    if self.is_global_downtime(current_time):
                        is_damage_immune = True

                skill_count_map[name] += 1
                step_total_damage = 0
                main_crit = False
                main_dh = False
                is_aoe = bool(payload.get('is_aoe', False))
                decay_rate = float(payload.get('decay', 0.0) or 0.0)
                active_buffs = self.get_active_damage_buffs(
                    buffs,
                    current_time,
                    job_state=job_state,
                    target_id=target_id,
                )
                if "smn_searing_snapshot" in payload:
                    snap = bool(payload["smn_searing_snapshot"])
                    current = bool(active_buffs.get("smn_searing"))
                    if snap != current:
                        active_buffs["damage_mult"] *= 1.05 if snap else (1.0 / 1.05)
                    active_buffs["smn_searing"] = snap
                if not is_damage_immune:
                    skill_target_sum_map[name] += target_count
                    total_hits_in_run += 1
                    for i in range(target_count):
                        dmg_val, is_c, is_d = self.calculate_damage_val(
                            potency,
                            is_auto=False,
                            is_dot=payload.get('is_dot', False),
                            active_buffs=active_buffs,
                            guaranteed_crit=payload.get('guaranteed_crit', False),
                            guaranteed_dh=payload.get('guaranteed_dh', False),
                            has_potion=has_potion,
                            force_no_crit=payload.get('force_no_crit', False),
                            force_no_dh=payload.get('force_no_dh', False),
                            job_mod_override=payload.get('job_mod_override'),
                        )
                        modifier = 1.0 - decay_rate if is_aoe and i > 0 else 1.0
                        step_total_damage += dmg_val * modifier
                        if i == 0:
                            main_crit = is_c
                            main_dh = is_d

                total_damage += step_total_damage
                skill_dmg_map[name] += step_total_damage
                if main_crit: skill_crit_map[name] += 1
                if main_dh: skill_dh_map[name] += 1
                if main_crit and main_dh: skill_cdh_map[name] += 1

                if is_first_run and potency > 0:
                    b_list = job_state.format_buffs(active_buffs, has_potion)
                    effective_potency, potency_formula, potency_buffs = self.potency_breakdown(
                        potency, potency, active_buffs, target_count, is_aoe, decay_rate
                    )
                    dmg_str = f"{step_total_damage:,.0f}"
                    if is_damage_immune:
                        dmg_str += " (免疫)"
                    combat_log.append({
                        'time': current_time, 'name': name, 'potency': potency,
                        'base_potency': potency,
                        'effective_potency': effective_potency,
                        'potency_formula': potency_formula,
                        'potency_buffs': potency_buffs,
                        'buffs': "+".join(b_list) if b_list else "-",
                        'crit': "✔" if main_crit else "",
                        'dh': "✔" if main_dh else "",
                        'dmg': dmg_str,
                        'targets': target_count,
                        'target_count': target_count,
                    })

            elif ev_type == SimEventType.AUTO_ATTACK_CHECK:
                if abs(payload['scheduled_time'] - next_aa_timestamp) > 0.0001: continue
                if not job_state.allows_auto_attack_at(current_time):
                    aa_running = False
                    continue
                if self.is_global_downtime(current_time):
                    aa_running = False;
                    continue
                c_start, c_end, c_slide = casting_state

                is_potion = (potion_active_until > current_time)
                aa_buffs = self.get_active_damage_buffs(buffs, current_time, job_state=job_state, target_id=1)
                if "auto_damage_mult" in aa_buffs:
                    aa_buffs["damage_mult"] = aa_buffs["auto_damage_mult"]
                push_sim_event(
                    pq,
                    current_time + AA_DELAY,
                    SimEventType.AUTO_ATTACK_DAMAGE,
                    tie_breaker,
                    {'has_potion': is_potion, 'active_buffs': aa_buffs},
                )
                interval = self.stats['delay'] * job_state.auto_attack_interval_multiplier(current_time)
                next_aa_timestamp = current_time + interval
                push_sim_event(
                    pq,
                    next_aa_timestamp,
                    SimEventType.AUTO_ATTACK_CHECK,
                    tie_breaker,
                    {'scheduled_time': next_aa_timestamp},
                )

            elif ev_type == SimEventType.AUTO_ATTACK_DAMAGE:
                if not job_state.allows_auto_attack_at(current_time):
                    continue
                if not self.is_global_downtime(current_time):
                    d = payload
                    skill_count_map['Auto Attack'] += 1;
                    skill_target_sum_map['Auto Attack'] += 1;
                    total_hits_in_run += 1
                    dmg, is_c, is_d = self.calculate_damage_val(AA_POTENCY, is_auto=True,
                                                                active_buffs=d.get('active_buffs', {}),
                                                                has_potion=d['has_potion'])
                    total_damage += dmg
                    skill_dmg_map['Auto Attack'] += dmg
                    if is_c: skill_crit_map['Auto Attack'] += 1
                    if is_d: skill_dh_map['Auto Attack'] += 1
                    if is_c and is_d: skill_cdh_map['Auto Attack'] += 1
                    if is_first_run:
                        active_buffs = d.get('active_buffs', {})
                        b_list = job_state.format_buffs(active_buffs, d['has_potion'])
                        effective_potency, potency_formula, potency_buffs = self.potency_breakdown(
                            AA_POTENCY, AA_POTENCY, active_buffs
                        )
                        combat_log.append({'time': current_time, 'name': 'Auto Attack', 'potency': AA_POTENCY,
                                           'base_potency': AA_POTENCY, 'effective_potency': effective_potency,
                                           'potency_formula': potency_formula,
                                           'potency_buffs': potency_buffs,
                                           'buffs': "+".join(b_list) if b_list else "-", 'crit': "✔" if is_c else "",
                                           'dh': "✔" if is_d else "", 'dmg': dmg, 'targets': 1, 'target_count': 1})

            elif ev_type == SimEventType.DOT_TICK:
                temp_active_dots = []
                for dot in active_dots:
                    if dot['expire'] < current_time: continue
                    if not job_state.is_dot_active(dot, current_time): continue
                    temp_active_dots.append(dot)
                    is_tick_blocked = False
                    if self.multi_boss_mode:
                        is_tick_blocked = self.is_target_untargetable(current_time, dot['tid'])
                    else:
                        is_tick_blocked = self.is_global_downtime(current_time)
                    if is_tick_blocked:
                        detail = dot.get('detail')
                        if detail is not None:
                            missed_targets = int(dot.get('targets', 1) or 1)
                            detail['missed_tick_events'] += 1
                            detail['missed_ticks'] += missed_targets
                        continue

                    tick_targets = int(dot.get('targets', 1) or 1)
                    tick_damage = 0.0
                    first_c = False
                    first_d = False
                    for i in range(tick_targets):
                        dmg, is_c, is_d = self.calculate_damage_val(
                            dot['potency'], is_dot=True, active_buffs=dot['buffs'],
                            guaranteed_crit=dot.get('guaranteed_crit', False),
                            guaranteed_dh=dot.get('guaranteed_dh', False),
                            has_potion=dot['has_potion'])
                        tick_damage += dmg
                        if i == 0:
                            first_c = is_c
                            first_d = is_d
                    dot_source_name = dot.get('source_name') or str(dot.get('name', 'Dot Tick')).replace(' (dot)', '')
                    skill_count_map[dot_source_name] += 1;
                    skill_target_sum_map[dot_source_name] += tick_targets;
                    total_hits_in_run += 1
                    total_damage += tick_damage
                    skill_dmg_map[dot_source_name] += tick_damage
                    if first_c: skill_crit_map[dot_source_name] += 1
                    if first_d: skill_dh_map[dot_source_name] += 1
                    if first_c and first_d: skill_cdh_map[dot_source_name] += 1
                    detail = dot.get('detail')
                    if detail is not None:
                        detail['tick_events'] += 1
                        detail['ticks'] += tick_targets
                        detail['damage'] += tick_damage
                        if first_c: detail['crit_ticks'] += 1
                        if first_d: detail['dh_ticks'] += 1
                        detail['last_tick_time'] = current_time
                    if is_first_run:
                        b_list = job_state.format_buffs(dot['buffs'], dot['has_potion'])
                        t_lbl = f"DoT(T{dot['tid']})" if (self.multi_boss_mode or dot.get('target_explicit')) else "DoT"
                        effective_potency, potency_formula, potency_buffs = self.potency_breakdown(
                            dot['potency'], dot['potency'], dot['buffs'], dot.get('targets', 1)
                        )
                        combat_log.append({'time': current_time, 'name': f"{dot['name']} (Tick)", 'potency': dot['potency'],
                                           'base_potency': dot['potency'], 'effective_potency': effective_potency,
                                           'potency_formula': potency_formula,
                                           'potency_buffs': potency_buffs,
                                           'buffs': "+".join(b_list) if b_list else "-", 'crit': "✔" if first_c else "",
                                           'dh': "✔" if first_d else "", 'dmg': tick_damage, 'targets': t_lbl,
                                           'target_count': int(dot.get('targets', 1) or 1)})
                active_dots = temp_active_dots
                push_sim_event(pq, current_time + 3.0, SimEventType.DOT_TICK, tie_breaker, None)

        self.last_dot_details = dot_details
        return (total_damage, last_skill_hit_time, skill_dmg_map, skill_count_map, skill_crit_map, skill_dh_map,
                skill_cdh_map, total_hits_in_run, combat_log, skill_target_sum_map, run_snapshots, history_snapshots,
                job_state.get_resource_warnings())

    def run_batch(self, threshold=46000, progress_callback=None):
        if not self.timeline_data:
            self.timeline_data = [(0.0, "晓风", 1), (2.14, "阵风", 1), (4.28, "月光", 1), (6.42, "彼岸花", 1)]
        original_timeline = self.timeline_data
        dmg_list, dps_list = [], []
        skill_dps = defaultdict(list);
        skill_cnt = defaultdict(list)
        agg_cnt = Counter();
        agg_crit = Counter();
        agg_dh = Counter();
        agg_cdh = Counter()
        total_hits_list = [];
        first_log = [];
        first_resource_warnings = []
        first_dot_details = []
        sim_dur = 0;
        last_hit = 0

        max_dps_val = -1.0
        best_run_stats = {}

        agg_snapshots = defaultdict(list)

        try:
            update_step = max(10, self.iterations // 20)

            high_rd_runs = {}

            for i in range(self.iterations):
                is_first = (i == 0)
                (dmg, lh, s_dmg, s_cnt, s_crit, s_dh, s_cdh, tot_hits, log, s_targets,
                 r_snaps, h_snaps, resource_warnings) = self.run_one_simulation(is_first)
                if is_first:
                    first_log = log
                    first_resource_warnings = resource_warnings
                    first_dot_details = list(getattr(self, 'last_dot_details', []))
                    self.target_stats_snapshot = s_targets

                for st, sd in r_snaps.items():
                    agg_snapshots[st].append(sd)

                dur = self.get_effective_duration(lh)
                current_dps = dmg / dur

                if current_dps > max_dps_val:
                    max_dps_val = current_dps
                    best_run_stats = {
                        'count': s_cnt, 'crit': s_crit, 'dh': s_dh, 'cdh': s_cdh,
                        'targets': s_targets, 'dmg': s_dmg
                    }

                if current_dps >= threshold:
                    run_id = i + 1
                    high_rd_runs[run_id] = {
                        'rd': current_dps,
                        'history': h_snaps,
                        'dur': dur
                    }

                dmg_list.append(dmg);
                dps_list.append(current_dps);
                total_hits_list.append(tot_hits)
                all_k = set(s_dmg.keys())
                for k in all_k:
                    skill_dps[k].append(s_dmg[k] / dur);
                    skill_cnt[k].append(s_cnt[k])
                agg_cnt.update(s_cnt);
                agg_crit.update(s_crit);
                agg_dh.update(s_dh);
                agg_cdh.update(s_cdh)
                sim_dur = dur;
                last_hit = lh
                if progress_callback and (i % update_step == 0): progress_callback(i + 1)
        finally:
            self.timeline_data = original_timeline

        if progress_callback: progress_callback(self.iterations)

        stats_pkg = {
            'dps': skill_dps, 'count': skill_cnt,
            'agg_count': agg_cnt, 'agg_crit': agg_crit, 'agg_dh': agg_dh, 'agg_cdh': agg_cdh,
            'total_hits_list': total_hits_list,
            'target_stats': self.target_stats_snapshot,
            'best_run': best_run_stats,
            'interval_data': agg_snapshots,
            'high_rd_runs': high_rd_runs,
            'dot_details': first_dot_details,
            'resource_warnings': first_resource_warnings,
            'invalid_skill_events': build_invalid_skill_events(original_timeline, self.skill_resolver, first_resource_warnings),
            'skill_variants': build_skill_variant_rows(first_log),
        }
        return dps_list, sim_dur, last_hit, stats_pkg, first_log


SamuraiSimulator = DpsSimulator


# ==========================================
# 3. UI (Frontend)
# ==========================================
class DpsSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1400x950")

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

        try:
            for icon_name in ("FFXIV_SIM.png", "XIV_SIM.png", "SAM.png"):
                png_path = resource_path(icon_name)
                if os.path.exists(png_path):
                    img = tk.PhotoImage(file=png_path)
                    self.root.iconphoto(True, img)
                    break
            else:
                for icon_name in ("FFXIV_SIM.ico", "XIV_SIM.ico", "ffxiv_ndps.ico"):
                    ico_path = resource_path(icon_name)
                    if os.path.exists(ico_path):
                        self.root.iconbitmap(ico_path)
                        break
        except Exception:
            pass

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.colors = {"bg": "#2b2b2b", "fg": "#ffffff", "panel": "#3c3f41", "accent": "#4a90e2", "text_bg": "#1e1e1e"}

        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["fg"],
                             font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), background=self.colors["bg"])
        self.style.configure("TLabelframe", background=self.colors["panel"], relief="flat")
        self.style.configure("TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["accent"],
                             font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=5, background=self.colors["accent"],
                             foreground="white", borderwidth=0)
        self.style.map("TButton", background=[("active", "#357abd")])
        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("Segoe UI", 10))
        self.style.configure("Treeview", background=self.colors["text_bg"], foreground=self.colors["fg"],
                             fieldbackground=self.colors["text_bg"], font=("Consolas", 10), rowheight=28)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", self.colors["accent"])])

        main_container = ttk.Frame(root, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        ttk.Label(main_container, text=APP_TITLE, style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        ctrl_fr = ttk.Frame(main_container);
        ctrl_fr.pack(fill=tk.X)
        left = ttk.Frame(ctrl_fr);
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        s_fr = ttk.LabelFrame(left, text=" 属性 ", padding=10);
        s_fr.pack(fill=tk.BOTH, expand=True)
        self.ents = {}
        self.job_var = tk.StringVar(value="SAM")
        ttk.Label(s_fr, text="职业").grid(row=0, column=0, sticky="w", pady=4)
        self.cmb_job = ttk.Combobox(s_fr, textvariable=self.job_var, width=10, state="readonly",
                                    values=list(DPS_JOB_ORDER))
        self.cmb_job.grid(row=0, column=1, padx=5)
        def on_job_selected(_event):
            delay_entry = self.ents.get("攻击间隔")
            if delay_entry is not None:
                delay_entry.delete(0, tk.END)
                delay_entry.insert(0, str(DEFAULT_WEAPON_DELAYS.get(self.job_var.get(), 2.64)))
            main_entry = self.ents.get("主属性")
            if main_entry is not None:
                main_entry.delete(0, tk.END)
                main_entry.insert(0, str(DEFAULT_MAIN_STATS.get(self.job_var.get(), SELF_TEST_BASE_STATS["main_stat"])))
            if self.csv_path:
                self.process_files()
        self.cmb_job.bind("<<ComboboxSelected>>", on_job_selected)
        defs = {"主属性": "6498", "暴击 (CRT)": "3605", "信念 (DET)": "2426", "直击 (DHT)": "1793",
                "速度 (SKS/SPS)": "689", "武器性能": "158", "攻击间隔": "2.64", "队伍加成": "1.05", "模拟次数": "10000", "RD筛选阈值": "46000"}
        defs["游戏版本"] = "7.5"
        r = 1
        for k, v in defs.items():
            ttk.Label(s_fr, text=k).grid(row=r, column=0, sticky="w", pady=4)
            e = ttk.Entry(s_fr, width=12);
            e.insert(0, v);
            e.grid(row=r, column=1, padx=5);
            self.ents[k] = e;
            r += 1

        right = ttk.Frame(ctrl_fr);
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tl_fr = ttk.LabelFrame(right, text=" 技能轴与目标数据 ", padding=10);
        tl_fr.pack(fill=tk.X, pady=(0, 10))
        b_box = ttk.Frame(tl_fr);
        b_box.pack(fill=tk.X)

        self.csv_path = None;
        self.txt_path = None
        self.downtime_track_path = None
        self.txt_downtime_windows = []
        self.txt_record_config = {}
        self.auto_downtime_path = None
        self.user_dot_config = {};
        self.user_downtime_config = defaultdict(list)

        ttk.Button(b_box, text="1. 导入轴 (CSV)", command=self.load_csv).pack(side=tk.LEFT)
        ttk.Button(b_box, text="2. 导入目标 (TXT)", command=self.load_txt).pack(side=tk.LEFT, padx=5)
        ttk.Button(b_box, text="3. 导入上天轨道 (TXT)", command=self.load_downtime_track).pack(side=tk.LEFT, padx=5)
        ttk.Button(b_box, text="4. 配置 DoT与上天", command=self.open_dot_config).pack(side=tk.LEFT, padx=5)
        self.lbl_st = ttk.Label(b_box, text="等待导入...", foreground="#aaaaaa");
        self.lbl_st.pack(side=tk.LEFT, padx=10)

        opt_fr = ttk.Frame(tl_fr);
        opt_fr.pack(fill=tk.X, pady=(5, 0))
        self.var_multi_boss = tk.BooleanVar(value=False)
        self.chk_multi = ttk.Checkbutton(opt_fr, text="开启多 Boss / 分路 DoT 模式 (自动计算上天交集)",
                                         variable=self.var_multi_boss)
        self.chk_multi.pack(side=tk.LEFT)

        ttk.Label(opt_fr, text=" | 自定义RD快照点(秒,逗号分隔):", foreground=self.colors["accent"]).pack(side=tk.LEFT,
                                                                                                         padx=(10, 2))
        self.entry_custom_snaps = ttk.Entry(opt_fr, width=20)
        self.entry_custom_snaps.insert(0, "")  # 默认留空，按需输入例如: 60, 150.5, 300
        self.entry_custom_snaps.pack(side=tk.LEFT)

        dt_fr = ttk.LabelFrame(right, text=" 全局上天时间 (仅单模式生效) ", padding=10);
        dt_fr.pack(fill=tk.BOTH, expand=True)
        self.txt_dt = tk.Text(dt_fr, height=4, bg=self.colors["text_bg"], fg="white", font=("Consolas", 10),
                              relief="flat")
        self.txt_dt.pack(fill=tk.BOTH);
        self.txt_dt.insert(tk.END, "(209.043, 221.343)\n")

        bot_fr = ttk.Frame(main_container);
        bot_fr.pack(fill=tk.X, pady=10)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(bot_fr, orient="horizontal", mode="determinate", variable=self.progress_var)
        self.progress.pack(fill=tk.X, pady=(0, 5))
        self.btn_run = ttk.Button(bot_fr, text="▶ 运行模拟", command=self.start_thread)
        self.btn_run.pack(fill=tk.X)
        export_fr = ttk.Frame(bot_fr)
        export_fr.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(export_fr, text="导出 Markdown 报告", command=self.export_markdown_report).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(export_fr, text="导出 CSV 明细", command=self.export_csv_details).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        self.nb = ttk.Notebook(main_container);
        self.nb.pack(fill=tk.BOTH, expand=True)

        self.tab_coverage = ttk.Frame(self.nb);
        self.nb.add(self.tab_coverage, text="导入覆盖")
        self.txt_coverage = scrolledtext.ScrolledText(self.tab_coverage, bg=self.colors["text_bg"], fg="white",
                                                      height=7, font=("Consolas", 10), relief="flat")
        self.txt_coverage.pack(fill=tk.X, padx=5, pady=(5, 0))
        cols_cov = ("status", "skill", "raw", "count", "targets", "tags", "reason")
        self.tree_coverage = ttk.Treeview(self.tab_coverage, columns=cols_cov, show="headings", height=16)
        self.tree_coverage.heading("status", text="分类")
        self.tree_coverage.column("status", width=95, anchor="center")
        self.tree_coverage.heading("skill", text="模拟技能名")
        self.tree_coverage.column("skill", width=160, anchor="w")
        self.tree_coverage.heading("raw", text="CSV 原名")
        self.tree_coverage.column("raw", width=160, anchor="w")
        self.tree_coverage.heading("count", text="次数")
        self.tree_coverage.column("count", width=60, anchor="center")
        self.tree_coverage.heading("targets", text="目标/来源")
        self.tree_coverage.column("targets", width=110, anchor="center")
        self.tree_coverage.heading("tags", text="标签")
        self.tree_coverage.column("tags", width=180, anchor="w")
        self.tree_coverage.heading("reason", text="说明")
        self.tree_coverage.column("reason", width=360, anchor="w")
        sb_cov = ttk.Scrollbar(self.tab_coverage, orient="vertical", command=self.tree_coverage.yview)
        self.tree_coverage.configure(yscroll=sb_cov.set)
        self.tree_coverage.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        sb_cov.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        self.tree_coverage.tag_configure("blocked", background="#6b2d2d", foreground="white")
        self.tree_coverage.tag_configure("warn", background="#5a4a20", foreground="white")
        self.tree_coverage.tag_configure("zero", background="#34445a", foreground="white")

        self.tab_preview = ttk.Frame(self.nb);
        self.nb.add(self.tab_preview, text="导入预览")
        self.txt_preview = scrolledtext.ScrolledText(self.tab_preview, bg=self.colors["text_bg"], fg="white",
                                                     height=3, font=("Consolas", 10), relief="flat")
        self.txt_preview.pack(fill=tk.X, padx=5, pady=(5, 0))
        cols_preview = ("row", "time", "skill", "raw", "gcd", "cast", "targets", "source")
        self.tree_preview = ttk.Treeview(self.tab_preview, columns=cols_preview, show="headings", height=20)
        preview_defs = [
            ("row", "CSV行", 70, "center"),
            ("time", "时间", 80, "center"),
            ("skill", "模拟技能名", 180, "w"),
            ("raw", "CSV 原名", 180, "w"),
            ("gcd", "GCD", 70, "center"),
            ("cast", "读条", 70, "center"),
            ("targets", "目标/来源", 110, "center"),
            ("source", "来源", 130, "center"),
        ]
        for key, label, width, anchor in preview_defs:
            self.tree_preview.heading(key, text=label)
            self.tree_preview.column(key, width=width, anchor=anchor)
        sb_preview = ttk.Scrollbar(self.tab_preview, orient="vertical", command=self.tree_preview.yview)
        self.tree_preview.configure(yscroll=sb_preview.set)
        self.tree_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        sb_preview.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

        self.tab_overview = ttk.Frame(self.nb);
        self.nb.add(self.tab_overview, text="模拟报告 (概览)")
        self.txt_res = scrolledtext.ScrolledText(self.tab_overview, bg=self.colors["text_bg"], fg="white",
                                                 font=("Consolas", 11), relief="flat")
        self.txt_res.pack(fill=tk.BOTH, expand=True)
        self.txt_res.tag_config("h1", foreground="#4a90e2", font=("Consolas", 12, "bold"))
        self.txt_res.tag_config("h2", foreground="#e5c07b", font=("Consolas", 11, "bold"))

        self.tab_log = ttk.Frame(self.nb);
        self.nb.add(self.tab_log, text="战斗日志 (表格)")
        cols_log = ("time", "skill", "pot", "buffs", "targets", "crit", "dh", "dmg")
        self.tree_log = ttk.Treeview(self.tab_log, columns=cols_log, show="headings", height=20)
        self.tree_log.heading("time", text="Time (s)");
        self.tree_log.column("time", width=80, anchor="center")
        self.tree_log.heading("skill", text="Skill Name");
        self.tree_log.column("skill", width=160, anchor="w")
        self.tree_log.heading("pot", text="Potency");
        self.tree_log.column("pot", width=60, anchor="center")
        self.tree_log.heading("buffs", text="Active Buffs");
        self.tree_log.column("buffs", width=120, anchor="w")
        self.tree_log.heading("targets", text="Targets");
        self.tree_log.column("targets", width=80, anchor="center")
        self.tree_log.heading("crit", text="Crit");
        self.tree_log.column("crit", width=50, anchor="center")
        self.tree_log.heading("dh", text="DH");
        self.tree_log.column("dh", width=50, anchor="center")
        self.tree_log.heading("dmg", text="Damage");
        self.tree_log.column("dmg", width=100, anchor="e")
        sb_log = ttk.Scrollbar(self.tab_log, orient="vertical", command=self.tree_log.yview)
        self.tree_log.configure(yscroll=sb_log.set)
        self.tree_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True);
        sb_log.pack(side=tk.RIGHT, fill=tk.Y)

        self.tab_dot_details = ttk.Frame(self.nb);
        self.nb.add(self.tab_dot_details, text="DoT 明细")
        cols_dot = ("id", "apply", "source", "dot", "target", "pot", "ticks", "missed", "dmg", "last", "buffs")
        self.tree_dot_details = ttk.Treeview(self.tab_dot_details, columns=cols_dot, show="headings", height=20)
        dot_defs = [
            ("id", "ID", 55, "center"),
            ("apply", "挂载时间", 90, "center"),
            ("source", "来源技能", 150, "w"),
            ("dot", "DoT", 150, "w"),
            ("target", "目标", 70, "center"),
            ("pot", "Potency", 75, "center"),
            ("ticks", "命中跳数", 80, "center"),
            ("missed", "丢失跳数", 80, "center"),
            ("dmg", "总伤害", 110, "e"),
            ("last", "最后一跳", 90, "center"),
            ("buffs", "快照 Buff", 180, "w"),
        ]
        for key, label, width, anchor in dot_defs:
            self.tree_dot_details.heading(key, text=label)
            self.tree_dot_details.column(key, width=width, anchor=anchor)
        sb_dot = ttk.Scrollbar(self.tab_dot_details, orient="vertical", command=self.tree_dot_details.yview)
        self.tree_dot_details.configure(yscroll=sb_dot.set)
        self.tree_dot_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        sb_dot.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

        self.tab_stats = ttk.Frame(self.nb);
        self.nb.add(self.tab_stats, text="技能统计 (平均)")
        cols_stats = ("skill", "count", "avg_t", "dps", "crit", "dh", "cdh")
        self.tree_stats = ttk.Treeview(self.tab_stats, columns=cols_stats, show="headings")
        self.tree_stats.heading("skill", text="Skill Name");
        self.tree_stats.column("skill", width=160, anchor="w")
        self.tree_stats.heading("count", text="Count");
        self.tree_stats.column("count", width=60, anchor="center")
        self.tree_stats.heading("avg_t", text="Avg Hits");
        self.tree_stats.column("avg_t", width=70, anchor="center")
        self.tree_stats.heading("dps", text="DPS (μ ± σ)");
        self.tree_stats.column("dps", width=200, anchor="center")
        self.tree_stats.heading("crit", text="Crit %");
        self.tree_stats.column("crit", width=80, anchor="center")
        self.tree_stats.heading("dh", text="DH %");
        self.tree_stats.column("dh", width=80, anchor="center")
        self.tree_stats.heading("cdh", text="CDH %");
        self.tree_stats.column("cdh", width=80, anchor="center")
        sb_stats = ttk.Scrollbar(self.tab_stats, orient="vertical", command=self.tree_stats.yview)
        self.tree_stats.configure(yscroll=sb_stats.set)
        self.tree_stats.pack(side=tk.LEFT, fill=tk.BOTH, expand=True);
        sb_stats.pack(side=tk.RIGHT, fill=tk.Y)

        self.tab_skill_variants = ttk.Frame(self.nb)
        self.nb.add(self.tab_skill_variants, text="技能详情 (Buff/目标)")
        cols_variants = ("skill", "targets", "buffs", "effective", "count", "formula")
        self.tree_skill_variants = ttk.Treeview(
            self.tab_skill_variants, columns=cols_variants, show="headings", height=20
        )
        variant_defs = [
            ("skill", "技能", 160, "w"),
            ("targets", "目标数", 65, "center"),
            ("buffs", "Buff", 180, "w"),
            ("effective", "实际威力", 90, "e"),
            ("count", "数量", 60, "center"),
            ("formula", "威力计算", 380, "w"),
        ]
        for key, label, width, anchor in variant_defs:
            self.tree_skill_variants.heading(key, text=label)
            self.tree_skill_variants.column(key, width=width, anchor=anchor)
        sb_variants = ttk.Scrollbar(
            self.tab_skill_variants, orient="vertical", command=self.tree_skill_variants.yview
        )
        self.tree_skill_variants.configure(yscroll=sb_variants.set)
        self.tree_skill_variants.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_variants.pack(side=tk.RIGHT, fill=tk.Y)

        self.tab_best = ttk.Frame(self.nb);
        self.nb.add(self.tab_best, text="极值详情 (Max DPS)")
        cols_best = ("skill", "count", "hits", "dmg", "crit", "dh", "cdh")
        self.tree_best = ttk.Treeview(self.tab_best, columns=cols_best, show="headings")
        self.tree_best.heading("skill", text="Skill Name");
        self.tree_best.column("skill", width=160, anchor="w")
        self.tree_best.heading("count", text="Cast");
        self.tree_best.column("count", width=60, anchor="center")
        self.tree_best.heading("hits", text="Total Hits");
        self.tree_best.column("hits", width=80, anchor="center")
        self.tree_best.heading("dmg", text="Total Damage");
        self.tree_best.column("dmg", width=100, anchor="center")
        self.tree_best.heading("crit", text="Crit %");
        self.tree_best.column("crit", width=70, anchor="center")
        self.tree_best.heading("dh", text="DH %");
        self.tree_best.column("dh", width=70, anchor="center")
        self.tree_best.heading("cdh", text="CDH %");
        self.tree_best.column("cdh", width=70, anchor="center")
        sb_best = ttk.Scrollbar(self.tab_best, orient="vertical", command=self.tree_best.yview)
        self.tree_best.configure(yscroll=sb_best.set)
        self.tree_best.pack(side=tk.LEFT, fill=tk.BOTH, expand=True);
        sb_best.pack(side=tk.RIGHT, fill=tk.Y)

        self.tab_intervals = ttk.Frame(self.nb);
        self.nb.add(self.tab_intervals, text="阶段 RD 分析")

        # 定义列：时间, 期望RD, Max RD, 1%水位, 0.1%水位
        cols_int = ("time", "mean_rd", "std_rd", "min_rd", "max_rd")
        self.tree_intervals = ttk.Treeview(self.tab_intervals, columns=cols_int, show="headings")

        self.tree_intervals.heading("time", text="时间节点")
        self.tree_intervals.heading("mean_rd", text="RD (μ ± σ)")
        self.tree_intervals.heading("std_rd", text="Max RD")  # 这里借个位置显示最大值
        self.tree_intervals.heading("min_rd", text="Top 1% (Z=2.326)")
        self.tree_intervals.heading("max_rd", text="Top 0.1% (Z=3.090)")

        # 设置列宽
        self.tree_intervals.column("time", width=100, anchor="center")
        self.tree_intervals.column("mean_rd", width=150, anchor="center")
        self.tree_intervals.column("std_rd", width=100, anchor="center")
        self.tree_intervals.column("min_rd", width=120, anchor="center")
        self.tree_intervals.column("max_rd", width=120, anchor="center")

        self.tree_intervals.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_int = ttk.Scrollbar(self.tab_intervals, orient="vertical", command=self.tree_intervals.yview)
        self.tree_intervals.configure(yscroll=sb_int.set)
        self.tree_intervals.pack(side=tk.LEFT, fill=tk.BOTH, expand=True);
        sb_int.pack(side=tk.RIGHT, fill=tk.Y)

        self.tab_viz = ttk.Frame(self.nb);
        self.nb.add(self.tab_viz, text="DPS 分布分析")
        self.frame_plot = ttk.Frame(self.tab_viz);
        self.frame_plot.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if not HAS_MATPLOTLIB:
            ttk.Label(self.frame_plot, text="请安装 matplotlib 以查看分布图", foreground="red",
                      font=("Segoe UI", 14)).pack(expand=True)

        self.tab_dist_table = ttk.Frame(self.nb);
        self.nb.add(self.tab_dist_table, text="DPS分布表格")
        cols_dist = ("range", "count", "percent")
        self.tree_dist = ttk.Treeview(self.tab_dist_table, columns=cols_dist, show="headings")
        self.tree_dist.heading("range", text="DPS 区间");
        self.tree_dist.column("range", width=150, anchor="center")
        self.tree_dist.heading("count", text="频次");
        self.tree_dist.column("count", width=100, anchor="center")
        self.tree_dist.heading("percent", text="上位占比 (≥Min)");
        self.tree_dist.column("percent", width=120, anchor="center")
        sb_dist = ttk.Scrollbar(self.tab_dist_table, orient="vertical", command=self.tree_dist.yview)
        self.tree_dist.configure(yscroll=sb_dist.set)
        self.tree_dist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        sb_dist.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.loaded = []
        self.coverage_report = None
        self.csv_meta = {}
        self.last_result_data = None
        self.last_report_metadata = {}

    def update_coverage_tab(self):
        for item in self.tree_coverage.get_children():
            self.tree_coverage.delete(item)
        self.txt_coverage.config(state=tk.NORMAL)
        self.txt_coverage.delete("1.0", tk.END)

        if not self.coverage_report:
            self.txt_coverage.insert(tk.END, "导入 CSV 后会在这里显示技能覆盖、未识别技能和当前可信度。")
            self.txt_coverage.config(state=tk.DISABLED)
            return

        self.txt_coverage.insert(tk.END, format_coverage_summary(self.coverage_report))
        self.txt_coverage.config(state=tk.DISABLED)

        for row in self.coverage_report["rows"]:
            cls = row["classification"]
            if cls["category"] == "unrecognized":
                tags = ("blocked",)
            elif cls["needs_state"] or cls["followup_unmodeled"]:
                tags = ("warn",)
            elif cls["category"] == "zero_damage":
                tags = ("zero",)
            else:
                tags = ()
            target_text = f"{row['max_targets']} / {row['target_sources_text']}"
            self.tree_coverage.insert("", tk.END, values=(
                cls["category_label"],
                row["name"],
                row["raw_name"],
                row["count"],
                target_text,
                row["tags_text"],
                cls["reason"],
            ), tags=tags)

    def clear_coverage_tab(self, message="导入 CSV 后会在这里显示技能覆盖、未识别技能和当前可信度。"):
        self.coverage_report = None
        for item in self.tree_coverage.get_children():
            self.tree_coverage.delete(item)
        self.txt_coverage.config(state=tk.NORMAL)
        self.txt_coverage.delete("1.0", tk.END)
        self.txt_coverage.insert(tk.END, message)
        self.txt_coverage.config(state=tk.DISABLED)

    def update_preview_tab(self, csv_meta=None):
        csv_meta = csv_meta or {}
        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)
        self.txt_preview.config(state=tk.NORMAL)
        self.txt_preview.delete("1.0", tk.END)
        if not self.loaded:
            self.txt_preview.insert(tk.END, "导入 CSV 后会在这里显示标准化后的前 20 行事件。")
            self.txt_preview.config(state=tk.DISABLED)
            return

        self.txt_preview.insert(
            tk.END,
            f"显示前 {min(20, len(self.loaded))} / {len(self.loaded)} 行 | "
            f"CSV 格式: {csv_meta.get('format', '-')} | "
            f"castTime: {'有' if csv_meta.get('has_cast_time') else '无'} | "
            f"isGCD: {'有' if csv_meta.get('has_is_gcd') else '无'}"
        )
        self.txt_preview.config(state=tk.DISABLED)

        for event in self.loaded[:20]:
            entry = timeline_entry(event)
            is_gcd = entry.get("is_gcd")
            if is_gcd is True:
                gcd_text = "GCD"
            elif is_gcd is False:
                gcd_text = "oGCD"
            else:
                gcd_text = "-"
            cast_time = entry.get("cast_time")
            cast_text = "-" if cast_time is None else f"{float(cast_time):.2f}"
            target_text = f"{entry.get('targets', 1)} / {entry.get('target_source', 'default')}"
            self.tree_preview.insert("", tk.END, values=(
                entry.get("row_no", "-"),
                f"{float(entry.get('time', 0.0)):.3f}",
                entry.get("name", ""),
                entry.get("raw_name", entry.get("name", "")),
                gcd_text,
                cast_text,
                target_text,
                entry.get("source", "-"),
            ))

    def clear_preview_tab(self, message="导入 CSV 后会在这里显示标准化后的前 20 行事件。"):
        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)
        self.txt_preview.config(state=tk.NORMAL)
        self.txt_preview.delete("1.0", tk.END)
        self.txt_preview.insert(tk.END, message)
        self.txt_preview.config(state=tk.DISABLED)

    def load_csv(self):
        p = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not p: return
        self.csv_path = p
        self.process_files()

    def load_txt(self):
        p = filedialog.askopenfilename(filetypes=[("Text/JSON", "*.txt *.json"), ("Text Files", "*.txt"), ("JSON Files", "*.json")])
        if not p: return
        self.txt_path = p
        self.process_files()

    def load_downtime_track(self):
        p = filedialog.askopenfilename(filetypes=[("上天轨道 TXT/JSON", "*.txt *.json"), ("Text Files", "*.txt"), ("JSON Files", "*.json")])
        if not p: return
        self.downtime_track_path = p
        self.auto_downtime_path = None
        self.process_files()

    def selected_game_version(self):
        entry = self.ents.get("游戏版本") if hasattr(self, "ents") else None
        if entry is None:
            return "7.5"
        try:
            return f"{float(entry.get()):g}"
        except ValueError:
            return "7.5"

    def process_files(self):
        csv_name = os.path.basename(self.csv_path) if self.csv_path else "未加载"
        txt_name = os.path.basename(self.txt_path) if self.txt_path else "未加载"
        track_name = os.path.basename(self.downtime_track_path) if self.downtime_track_path else "未导入"

        if not self.csv_path:
            self.lbl_st.config(text="等待导入...", foreground="#aaaaaa")
            self.csv_meta = {}
            self.clear_coverage_tab()
            self.clear_preview_tab()
            return

        try:
            job_code = self.job_var.get() if hasattr(self, 'job_var') else "SAM"
            temp_csv, csv_meta = parse_axis_csv(
                self.csv_path,
                normalize_name=lambda raw_name: normalize_skill_name_for_job(raw_name, job_code)
            )
            self.csv_meta = csv_meta

            txt_skills = []
            self.txt_record_config = {}
            self.txt_downtime_windows = []
            if self.txt_path:
                with open(self.txt_path, 'r', encoding='utf-8-sig') as f:
                    txt_text = f.read()
                try:
                    log_data = json.loads(txt_text)
                    self.txt_record_config = log_data.get("config", {}) or {}
                    txt_skills = [x for x in log_data.get('actions', []) if x.get('type') == 'Skill']
                except json.JSONDecodeError:
                    txt_skills = []

            if self.downtime_track_path:
                with open(self.downtime_track_path, 'r', encoding='utf-8-sig') as f:
                    track_text = f.read()
                try:
                    track_data = json.loads(track_text)
                    self.txt_downtime_windows = parse_marker_track_downtime_windows(track_data)
                except json.JSONDecodeError:
                    self.txt_downtime_windows = parse_downtime_windows(track_text)

                if self.txt_downtime_windows and self.auto_downtime_path != self.downtime_track_path:
                    self.txt_dt.delete("1.0", tk.END)
                    self.txt_dt.insert(
                        tk.END,
                        "\n".join(f"{start:g}-{end:g}" for start, end in self.txt_downtime_windows) + "\n",
                    )
                    self.auto_downtime_path = self.downtime_track_path

            final_loaded = []
            txt_idx = 0;
            max_txt = len(txt_skills);
            search_window = 15
            for row in temp_csv:
                raw_name = row.get('raw_name', row['name']);
                sim_name = row['name']
                target_count = 1
                target_source = "default"
                target_ids = []
                if txt_skills:
                    for i in range(txt_idx, min(txt_idx + search_window, max_txt)):
                        txt_item = txt_skills[i];
                        txt_n = txt_item.get('skillName', "")
                        if skill_names_match(raw_name, sim_name, txt_n, job_code):
                            # === 修改开始：适配 targetList 格式 ===
                            if 'targetList' in txt_item:
                                # 如果有 targetList，目标数 = 列表长度
                                target_count = len(txt_item['targetList'])
                                target_ids = list(txt_item['targetList'])
                            else:
                                # 兼容旧格式
                                target_count = txt_item.get('targetCount', 1)
                            # === 修改结束 ===

                            txt_idx = i + 1;
                            target_source = "txt"

                            break
                row = dict(row)
                row['targets'] = int(target_count)
                if target_ids:
                    row['target_ids'] = target_ids
                row['target_source'] = target_source
                final_loaded.append(row)
            self.loaded = final_loaded
            self.last_result_data = None
            self.last_report_metadata = {}
            resolver = SkillResolver(job_code, self.selected_game_version())
            self.coverage_report = build_skill_coverage(final_loaded, resolver, csv_meta=csv_meta)
            self.update_coverage_tab()
            self.update_preview_tab(csv_meta)
            target_mode = txt_name if self.txt_path else "单目标模式"
            if self.txt_downtime_windows:
                track_mode = f"{track_name} ({len(self.txt_downtime_windows)} 段全局上天)"
            else:
                track_mode = track_name
            color = "#98c379" if (self.txt_path or self.downtime_track_path) else "#e5c07b"
            flags = []
            if csv_meta.get("has_cast_time"):
                flags.append("castTime")
            if csv_meta.get("has_is_gcd"):
                flags.append("isGCD")
            flag_text = f" | 字段: {', '.join(flags)}" if flags else ""
            skipped_text = f" | 跳过 {csv_meta['skipped']} 行" if csv_meta.get("skipped") else ""
            stats = self.coverage_report["stats"]
            coverage_text = f" | 覆盖: 未识别 {stats.get('unrecognized_events', 0)}, 状态: {self.coverage_report['status']}"
            self.lbl_st.config(
                text=f"CSV: {csv_name} ({csv_meta['format']}, {len(final_loaded)} 技能{flag_text}{skipped_text}) | 目标 TXT: {target_mode} | 上天轨道 TXT: {track_mode}{coverage_text}",
                foreground=color
            )
            self.nb.select(self.tab_coverage)
        except AxisCsvError as e:
            extra = ""
            if self.csv_path and "skillline" in os.path.basename(self.csv_path).lower():
                extra = "\n\n提示：这个文件看起来是 TTS skillline 导出，不是排轴网原始 CSV；程序已经尝试兼容解析。若仍失败，请换用含 time/action 列的原始排轴 CSV。"
            messagebox.showerror("处理错误", f"解析排轴 CSV 失败:\n{str(e)}{extra}")
            self.loaded = []
            self.csv_meta = {}
            self.clear_coverage_tab("解析排轴 CSV 失败，尚无覆盖报告。")
            self.clear_preview_tab("解析排轴 CSV 失败，尚无导入预览。")
        except Exception as e:
            messagebox.showerror("处理错误", f"解析文件失败:\n{str(e)}")
            self.loaded = []
            self.csv_meta = {}
            self.clear_coverage_tab("解析文件失败，尚无覆盖报告。")
            self.clear_preview_tab("解析文件失败，尚无导入预览。")

    def open_dot_config(self):
        if not self.loaded: messagebox.showwarning("提示", "请先导入技能轴！"); return
        resolver = SkillResolver(
            self.job_var.get() if hasattr(self, 'job_var') else "SAM",
            self.selected_game_version(),
        )
        found_dots = [];
        counts = defaultdict(int);
        max_target_id = 1
        for item in self.loaded:
            c = timeline_targets(item)
            if c > max_target_id: max_target_id = c
        for item in self.loaded:
            event = timeline_entry(item)
            t = event['time']
            name = event['name']
            skill_info = resolver.get(name)
            if skill_info and 'dot_potency' in skill_info:
                idx = counts[name];
                current_tid = 1
                if name in self.user_dot_config and idx < len(self.user_dot_config[name]):
                    current_tid = self.user_dot_config[name][idx]
                max_target_id = max(max_target_id, current_tid)
                found_dots.append({'name': name, 'time': t, 'idx': idx, 'tid': current_tid});
                counts[name] += 1
        if max_target_id < 2 and any(timeline_targets(x) > 1 for x in self.loaded): max_target_id = 2
        if not found_dots: messagebox.showinfo("提示", "轴内没有检测到 DoT 技能，无需配置目标。"); return

        win = tk.Toplevel(self.root)
        win.title("多目标与上天配置")
        win.geometry("600x700")
        
        try:
            for icon_name in ("FFXIV_SIM.png", "XIV_SIM.png", "SAM.png"):
                png_path = resource_path(icon_name)
                if os.path.exists(png_path):
                    win.icon_image = tk.PhotoImage(file=png_path)
                    win.iconphoto(False, win.icon_image)
                    break
            else:
                for icon_name in ("FFXIV_SIM.ico", "XIV_SIM.ico", "ffxiv_ndps.ico"):
                    ico_path = resource_path(icon_name)
                    if os.path.exists(ico_path):
                        win.iconbitmap(ico_path)
                        break
        except Exception:
            pass
        frame_top = ttk.LabelFrame(win, text="1. DoT 目标归属 (双击修改 ID)", padding=10)
        frame_top.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        cols = ("time", "name", "tid");
        tree = ttk.Treeview(frame_top, columns=cols, show="headings", height=8)
        tree.heading("time", text="时间");
        tree.column("time", width=80, anchor="center")
        tree.heading("name", text="技能");
        tree.column("name", width=120, anchor="center")
        tree.heading("tid", text="目标 ID");
        tree.column("tid", width=80, anchor="center")
        tree.pack(fill=tk.BOTH, expand=True)
        for item in found_dots:
            tree.insert("", tk.END, values=(f"{item['time']:.2f}", f"{item['name']} (#{item['idx'] + 1})", item['tid']),
                        tags=(item['name'], item['idx']))

        def on_double_click(event):
            item_id = tree.selection()[0];
            values = tree.item(item_id, "values")
            new_tid = simpledialog.askstring("设置目标 ID", f"设置 {values[1]} 的目标 ID (整数):",
                                             initialvalue=values[2], parent=win)
            if new_tid and new_tid.isdigit(): tree.set(item_id, "tid", new_tid)

        tree.bind("<Double-1>", on_double_click)

        frame_bot = ttk.LabelFrame(win, text="2. 各目标上天时间 (格式: 开始-结束, 开始-结束)", padding=10)
        frame_bot.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(frame_bot, text="示例: 0-15.5, 100-110 (英文逗号分隔)", foreground="gray").pack(anchor="w")
        dt_entries = {};
        display_rows = max(2, max_target_id)
        for i in range(1, display_rows + 1):
            row_f = ttk.Frame(frame_bot);
            row_f.pack(fill=tk.X, pady=2)
            ttk.Label(row_f, text=f"Target {i}:", width=10).pack(side=tk.LEFT)
            current_dt_list = self.user_downtime_config.get(i, [])
            default_str = ", ".join([f"{s}-{e}" for s, e in current_dt_list])
            entry = ttk.Entry(row_f);
            entry.insert(0, default_str);
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True);
            dt_entries[i] = entry

        def save_config():
            new_dot_config = defaultdict(list)
            for child in tree.get_children():
                vals = tree.item(child, "values");
                name_raw = vals[1].split(' (')[0];
                tid = int(vals[2])
                new_dot_config[name_raw].append(tid)
            self.user_dot_config = new_dot_config
            new_dt_config = defaultdict(list)
            for tid, entry in dt_entries.items():
                text = entry.get().strip()
                if not text: continue
                try:
                    parts = text.replace('，', ',').split(',')
                    for p in parts:
                        if '-' in p: s, e = map(float, p.split('-')); new_dt_config[tid].append((s, e))
                except ValueError:
                    messagebox.showerror("格式错误", f"Target {tid} 的时间格式错误。"); return
            self.user_downtime_config = new_dt_config
            messagebox.showinfo("成功", "配置已更新！");
            win.destroy()

        ttk.Button(win, text="保存并关闭", command=save_config).pack(pady=10)

    def get_main_page_dt(self):
        return parse_downtime_windows(self.txt_dt.get("1.0", tk.END))

    def calculate_global_downtime_intersection(self):
        if not self.user_downtime_config: return []
        lists = list(self.user_downtime_config.values())
        if not lists: return []
        current_intersection = sorted(lists[0])
        for next_list in lists[1:]:
            next_list = sorted(next_list);
            new_intersection = []
            i, j = 0, 0
            while i < len(current_intersection) and j < len(next_list):
                s1, e1 = current_intersection[i];
                s2, e2 = next_list[j]
                start = max(s1, s2);
                end = min(e1, e2)
                if start < end: new_intersection.append((start, end))
                if e1 < e2:
                    i += 1
                else:
                    j += 1
            current_intersection = new_intersection
            if not current_intersection: break
        return current_intersection

    def start_thread(self):
        if self.csv_path:
            self.process_files()
        self.btn_run.config(state="disabled", text="计算中...")
        self.progress_var.set(0)
        self.txt_res.delete("1.0", tk.END)
        for i in self.tree_log.get_children(): self.tree_log.delete(i)
        for i in self.tree_dot_details.get_children(): self.tree_dot_details.delete(i)
        for i in self.tree_stats.get_children(): self.tree_stats.delete(i)
        for i in self.tree_skill_variants.get_children(): self.tree_skill_variants.delete(i)
        for i in self.tree_best.get_children(): self.tree_best.delete(i)
        for i in self.tree_dist.get_children(): self.tree_dist.delete(i)
        for i in self.tree_intervals.get_children(): self.tree_intervals.delete(i)
        if HAS_MATPLOTLIB:
            for widget in self.frame_plot.winfo_children(): widget.destroy()
        t = threading.Thread(target=self.run_logic)
        t.start()

    def update_prog(self, v):
        self.progress_var.set(v)

    def run_logic(self):
        try:
            st = {k: float(v.get()) for k, v in self.ents.items()}
            job_code = self.job_var.get() if hasattr(self, 'job_var') else "SAM"
            profile = JOB_PROFILES.get(job_code, JOB_PROFILES.get("SAM"))
            st['job'] = job_code
            st['main_stat'] = int(st['主属性']);
            st['str'] = st['main_stat'];
            st['crt'] = int(st['暴击 (CRT)'])
            st['det'] = int(st['信念 (DET)']);
            st['dh'] = int(st['直击 (DHT)'])
            st['sks'] = int(st['速度 (SKS/SPS)']);
            st['wd'] = int(st['武器性能'])
            st['delay'] = float(st['攻击间隔']);
            st['version'] = f"{st['游戏版本']:g}"
            st['party_bonus'] = float(st['队伍加成']) if st.get('队伍加成') else profile.party_bonus
            mana_tick = (self.txt_record_config or {}).get("timeTillFirstManaTick")
            if mana_tick is not None:
                st['time_till_first_mana_tick'] = float(mana_tick)
            iters = int(st['模拟次数'])
            target_threshold = float(st.get('RD筛选阈值', 0.0))


            self.progress.config(maximum=iters)
            is_multi = self.var_multi_boss.get()
            final_dt_config = {}
            final_global_dt_list = []

            if is_multi:
                final_dt_config = self.user_downtime_config
                final_global_dt_list = self.calculate_global_downtime_intersection()
            else:
                main_dt = self.get_main_page_dt()
                final_global_dt_list = main_dt
                final_dt_config = {}

            custom_snaps_str = self.entry_custom_snaps.get().strip()
            custom_snaps_list = []
            if custom_snaps_str:
                try:
                    # 兼容中英文逗号
                    custom_snaps_list = [float(x.strip()) for x in custom_snaps_str.replace('，', ',').split(',') if
                                         x.strip()]
                except ValueError:
                    self.root.after(0,
                                    lambda: messagebox.showwarning("警告", "自定义快照点格式错误，已忽略。请填入数字。"))

            run_seed = random.randrange(1, 2 ** 31)
            random.seed(run_seed)

            sim = DpsSimulator(st, self.loaded,
                               downtime_config=final_dt_config,
                               dot_config=self.user_dot_config,
                               multi_boss_mode=is_multi,
                               global_downtime_list=final_global_dt_list,
                               iterations=iters,
                               custom_snaps=custom_snaps_list)

            dps_l, dur, last_h, stats_pkg, log = sim.run_batch(threshold=target_threshold, progress_callback=self.update_prog)

            m_dps = statistics.mean(dps_l)
            sd_dps = statistics.stdev(dps_l) if iters > 1 else 0
            base_gcd, shifu_gcd = DpsSimulator.calculate_gcd(st['sks'], job_code)

            ui_data = {
                'm_dps': m_dps, 'sd_dps': sd_dps, 'dur': dur, 'last_h': last_h,
                'stats_pkg': stats_pkg, 'log': log, 'dps_l': dps_l, 'iters': iters,
                'sim_instance': sim, 'gcd_info': (base_gcd, shifu_gcd), 'random_seed': run_seed
            }
            self.root.after(0, lambda: self.finish_ui(ui_data))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.btn_run.config(state="normal", text="▶ 运行模拟"))

    def has_xivintheshell_damage_xivintheshell(self):
        if not self.csv_path:
            return False
        directory = os.path.dirname(self.csv_path)
        if not os.path.isdir(directory):
            return False
        return any(name.endswith("_xivintheshell_damage.csv") for name in os.listdir(directory))

    def target_source_label(self):
        if self.txt_path:
            return f"{os.path.basename(self.txt_path)} (TXT/JSON target list)"
        if not self.coverage_report:
            return "default target=1"
        stats = self.coverage_report.get("stats", {})
        default_events = int(stats.get("default_target_events", 0) or 0)
        total_events = int(stats.get("total_events", 0) or 0)
        if default_events:
            return f"default target=1 for {default_events}/{total_events} rows"
        return "axis target metadata"

    def downtime_source_label(self, global_downtime_list=None):
        windows = global_downtime_list if global_downtime_list is not None else self.get_main_page_dt()
        count = len(windows or [])
        if self.var_multi_boss.get():
            return f"multi-boss intersection ({count} windows)"
        if self.downtime_track_path and self.txt_downtime_windows:
            return f"{os.path.basename(self.downtime_track_path)} ({len(self.txt_downtime_windows)} untargetable windows)"
        if count:
            return f"manual global downtime ({count} windows)"
        return "none"

    def evidence_status(self, resource_warnings=None):
        resource_warnings = resource_warnings or []
        stats = (self.coverage_report or {}).get("stats", {})
        coverage_ok = (
            int(stats.get("unrecognized_events", 0) or 0) == 0
            and int(stats.get("needs_state_events", 0) or 0) == 0
            and int(stats.get("followup_unmodeled_events", 0) or 0) == 0
        )
        import_status = "yes" if coverage_ok and self.loaded else "no"
        mechanic_status = "partial: xivintheshell damage baseline present" if self.has_xivintheshell_damage_xivintheshell() else "not established"
        if resource_warnings:
            mechanic_status += "; resource warnings need review"
        log_status = "no: requires real log / AMAS / audited external evidence"
        return {
            "import_smoke_passed": import_status,
            "mechanic_calibrated": mechanic_status,
            "log_validated": log_status,
        }

    def build_report_metadata(self, sim, stats_pkg, dur, last_h, m_dps, sd_dps, iters, random_seed=None):
        resource_warnings = stats_pkg.get("resource_warnings", [])
        evidence = self.evidence_status(resource_warnings)
        provider = "ama_xiv_combat_sim local provider" if getattr(sim.skill_resolver, "provider", None) else "local fallback skill table"
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app": APP_TITLE,
            "job": f"{sim.job_profile.name} ({sim.job})",
            "game_version": str(sim.stats.get("version", "7.5/default")),
            "skill_data_source": provider,
            "sample_path": self.csv_path or "-",
            "target_source": self.target_source_label(),
            "downtime_source": self.downtime_source_label(getattr(sim, "global_downtime_list", [])),
            "csv_format": self.csv_meta.get("format", "-"),
            "coverage_status": (self.coverage_report or {}).get("status", "-"),
            "resource_status": (
                f"{len(resource_warnings)} warning(s); trend-only interpretation"
                if resource_warnings else "no resource warnings"
            ),
            "import_smoke_passed": evidence["import_smoke_passed"],
            "mechanic_calibrated": evidence["mechanic_calibrated"],
            "log_validated": evidence["log_validated"],
            "iterations": iters,
            "random_seed": random_seed if random_seed is not None else "-",
            "duration": dur,
            "last_hit": last_h,
            "expected_dps": m_dps,
            "std_dps": sd_dps,
        }

    def insert_report_header(self, text_widget, metadata):
        text_widget.insert(tk.END, "【报告边界与可信等级】\n", "h2")
        text_widget.insert(tk.END, PERSONAL_NDPS_DEFINITION + "\n")
        text_widget.insert(tk.END, f"技能数据源: {metadata['skill_data_source']} | 游戏版本: {metadata['game_version']}\n")
        text_widget.insert(tk.END, f"模拟随机种子: {metadata['random_seed']}\n")
        text_widget.insert(tk.END, f"样本路径: {metadata['sample_path']}\n")
        text_widget.insert(tk.END, f"目标数来源: {metadata['target_source']} | CSV 格式: {metadata['csv_format']}\n")
        text_widget.insert(tk.END, f"上天时间来源: {metadata['downtime_source']}\n")
        text_widget.insert(
            tk.END,
            "可信等级: "
            f"import_smoke_passed={metadata['import_smoke_passed']}; "
            f"mechanic_calibrated={metadata['mechanic_calibrated']}; "
            f"log_validated={metadata['log_validated']}\n"
        )
        text_widget.insert(tk.END, f"资源合法性: {metadata['resource_status']}\n")
        text_widget.insert(tk.END, "-" * 50 + "\n\n")

    def skill_aggregate_rows(self, data):
        stats_pkg = data["stats_pkg"]
        sim = data["sim_instance"]
        iters = data["iters"]
        rows = []
        s_dps = stats_pkg["dps"]
        s_cnt = stats_pkg["count"]
        target_stats = stats_pkg.get("target_stats", {})
        agg_cnt = stats_pkg["agg_count"]
        agg_crit = stats_pkg["agg_crit"]
        agg_dh = stats_pkg["agg_dh"]
        agg_cdh = stats_pkg["agg_cdh"]
        for skill in sorted(s_dps.keys(), key=lambda x: statistics.mean(s_dps[x]), reverse=True):
            avg_count = statistics.mean(s_cnt[skill])
            total_hits = target_stats.get(skill, 0)
            avg_hits = total_hits / avg_count if avg_count > 0 else 0.0
            avg_dps = statistics.mean(s_dps[skill])
            sd_dps = statistics.stdev(s_dps[skill]) if iters > 1 else 0.0
            hit_count = agg_cnt[skill]
            if hit_count > 0:
                crit = agg_crit[skill] / hit_count * 100
                dh = agg_dh[skill] / hit_count * 100
                cdh = agg_cdh[skill] / hit_count * 100
            else:
                crit = dh = cdh = 0.0
            rows.append({
                "skill": skill,
                "avg_cast_count": round(avg_count, 3),
                "avg_hits_per_cast": round(avg_hits, 3),
                "avg_dps": round(avg_dps, 6),
                "std_dps": round(sd_dps, 6),
                "total_hit_events": int(hit_count),
                "crit_percent": round(crit, 3),
                "direct_hit_percent": round(dh, 3),
                "crit_direct_percent": round(cdh, 3),
                "known_skill": bool(sim.get_skill(skill)),
            })
        return rows

    @staticmethod
    def write_csv(path, rows, fields):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})

    def coverage_rows_for_export(self):
        rows = []
        if not self.coverage_report:
            return rows
        for row in self.coverage_report.get("rows", []):
            cls = row.get("classification", {})
            rows.append({
                "raw_name": row.get("raw_name", ""),
                "name": row.get("name", ""),
                "category": cls.get("category", ""),
                "category_label": cls.get("category_label", ""),
                "count": row.get("count", 0),
                "first_time": row.get("first_time", ""),
                "last_time": row.get("last_time", ""),
                "max_targets": row.get("max_targets", ""),
                "target_sources": row.get("target_sources_text", ""),
                "tags": row.get("tags_text", ""),
                "reason": cls.get("reason", ""),
            })
        return rows

    def markdown_report(self, data):
        metadata = self.last_report_metadata or self.build_report_metadata(
            data["sim_instance"], data["stats_pkg"], data["dur"], data["last_h"],
            data["m_dps"], data["sd_dps"], data["iters"], data.get("random_seed")
        )
        resource_warnings = data["stats_pkg"].get("resource_warnings", [])
        invalid_skill_events = data["stats_pkg"].get("invalid_skill_events", [])
        dot_details = data["stats_pkg"].get("dot_details", [])
        lines = [
            f"# {APP_TITLE} Report",
            "",
            f"Generated: {metadata['generated_at']}",
            "",
            "## Definition",
            "",
            PERSONAL_NDPS_DEFINITION,
            "",
            "## Evidence Status",
            "",
            f"- Import smoke passed: {metadata['import_smoke_passed']}",
            f"- Mechanic calibrated: {metadata['mechanic_calibrated']}",
            f"- Log validated: {metadata['log_validated']}",
            f"- Coverage status: {metadata['coverage_status']}",
            f"- Resource legality: {metadata['resource_status']}",
            "",
            "## Inputs",
            "",
            f"- Job: {metadata['job']}",
            f"- Game version: {metadata['game_version']}",
            f"- Skill data source: {metadata['skill_data_source']}",
            f"- Random seed: {metadata['random_seed']}",
            f"- Sample path: `{metadata['sample_path']}`",
            f"- Target source: {metadata['target_source']}",
            f"- Downtime source: {metadata['downtime_source']}",
            f"- CSV format: {metadata['csv_format']}",
            "",
            "## Results",
            "",
            f"- Iterations: {metadata['iterations']}",
            f"- Effective duration: {metadata['duration']:.3f}s",
            f"- Last hit: {metadata['last_hit']:.3f}s",
            f"- Expected DPS/RD: {metadata['expected_dps']:,.2f}",
            f"- Std dev: {metadata['std_dps']:,.2f}",
            "",
            "## Resource Warnings",
            "",
        ]
        if resource_warnings:
            for warning in resource_warnings:
                row = f"row {warning.get('row_no')} " if warning.get("row_no") is not None else ""
                lines.append(
                    f"- {row}{warning.get('time', '-') }s `{warning.get('skill', '-')}`: "
                    f"`{warning.get('code', 'warning')}` - {warning.get('message', '')}"
                )
        else:
            lines.append("- None.")
        lines.extend([
            "",
            "## Invalid Skill Events",
            "",
        ])
        if invalid_skill_events:
            for item in invalid_skill_events:
                row = f"row {item.get('row_no')} " if item.get("row_no") is not None else ""
                lines.append(
                    f"- {row}{item.get('time', '-') }s `{item.get('skill', '-')}`: "
                    f"`{item.get('kind', '-')}` - {item.get('reason', '')}"
                )
        else:
            lines.append("- None.")
        lines.extend([
            "",
            "## DoT Details",
            "",
        ])
        if dot_details:
            lines.extend([
                "| ID | Apply | Source | DoT | Target | Potency | Ticks | Missed | Damage | Last Tick | Buffs |",
                "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ])
            for item in sorted(dot_details, key=lambda row: (row.get("apply_time", 0), row.get("dot_id", 0))):
                last_tick_time = item.get("last_tick_time")
                last_tick_text = "-" if last_tick_time is None else f"{float(last_tick_time):.3f}"
                lines.append(
                    f"| {item.get('dot_id', '-')} | {float(item.get('apply_time', 0.0)):.3f} | "
                    f"{item.get('source_name', '-')} | {item.get('name', '-')} | "
                    f"T{item.get('target_id', '-')} | {item.get('potency', '-')} | "
                    f"{item.get('ticks', 0)} | {item.get('missed_ticks', 0)} | "
                    f"{float(item.get('damage', 0.0)):,.2f} | {last_tick_text} | {item.get('buffs_text', '-')} |"
                )
        else:
            lines.append("- None.")
        lines.extend([
            "",
            "## Top Skill DPS",
            "",
            "| Skill | Avg Count | Avg Hits/Cast | Avg DPS | Std DPS | Crit % | DH % | CDH % |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for row in self.skill_aggregate_rows(data)[:30]:
            lines.append(
                f"| {row['skill']} | {row['avg_cast_count']} | {row['avg_hits_per_cast']} | "
                f"{row['avg_dps']:.2f} | {row['std_dps']:.2f} | "
                f"{row['crit_percent']:.1f} | {row['direct_hit_percent']:.1f} | {row['crit_direct_percent']:.1f} |"
            )
        lines.extend([
            "",
            "## Caveat",
            "",
            "This report is a simulator artifact. Treat xivintheshell smoke/baseline comparisons as regression evidence, not FFLogs-equivalent log validation.",
            "",
        ])
        return "\n".join(lines)

    def export_markdown_report(self):
        if not self.last_result_data:
            messagebox.showwarning("尚无报告", "请先运行一次模拟。")
            return
        default_name = f"{self.job_var.get()}_ndps_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=default_name,
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.markdown_report(self.last_result_data))
        messagebox.showinfo("导出完成", f"Markdown 报告已导出:\n{path}")

    def export_csv_details(self):
        if not self.last_result_data:
            messagebox.showwarning("尚无明细", "请先运行一次模拟。")
            return
        out_dir = filedialog.askdirectory(title="选择 CSV 明细导出目录")
        if not out_dir:
            return
        os.makedirs(out_dir, exist_ok=True)
        prefix = f"{self.job_var.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        data = self.last_result_data
        metadata = self.last_report_metadata

        log_rows = []
        for row in sorted(data["log"], key=lambda x: x.get("time", 0)):
            log_rows.append({
                "time": row.get("time", ""),
                "skill": row.get("name", ""),
                "potency": row.get("potency", ""),
                "buffs": row.get("buffs", ""),
                "targets": row.get("targets", ""),
                "crit": row.get("crit", ""),
                "direct_hit": row.get("dh", ""),
                "damage": row.get("dmg", ""),
            })
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_combat_log.csv"),
            log_rows,
            ["time", "skill", "potency", "buffs", "targets", "crit", "direct_hit", "damage"],
        )
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_dot_details.csv"),
            data["stats_pkg"].get("dot_details", []),
            [
                "dot_id", "row_no", "apply_time", "source_name", "name", "target_id",
                "targets", "potency", "expire_time", "buffs_text", "has_potion",
                "tick_events", "ticks", "missed_tick_events", "missed_ticks",
                "damage", "crit_ticks", "dh_ticks", "last_tick_time",
            ],
        )
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_skill_aggregate.csv"),
            self.skill_aggregate_rows(data),
            [
                "skill", "avg_cast_count", "avg_hits_per_cast", "avg_dps", "std_dps",
                "total_hit_events", "crit_percent", "direct_hit_percent",
                "crit_direct_percent", "known_skill",
            ],
        )
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_coverage_report.csv"),
            self.coverage_rows_for_export(),
            [
                "raw_name", "name", "category", "category_label", "count", "first_time",
                "last_time", "max_targets", "target_sources", "tags", "reason",
            ],
        )
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_resource_warnings.csv"),
            data["stats_pkg"].get("resource_warnings", []),
            ["job", "row_no", "time", "skill", "code", "severity", "message"],
        )
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_invalid_skill_events.csv"),
            data["stats_pkg"].get("invalid_skill_events", []),
            ["row_no", "time", "skill", "kind", "code", "source", "reason"],
        )
        self.write_csv(
            os.path.join(out_dir, f"{prefix}_report_metadata.csv"),
            [metadata],
            [
                "generated_at", "app", "job", "game_version", "skill_data_source",
                "sample_path", "target_source", "downtime_source", "csv_format", "coverage_status",
                "resource_status", "import_smoke_passed", "mechanic_calibrated",
                "log_validated", "iterations", "random_seed", "duration", "last_hit",
                "expected_dps", "std_dps",
            ],
        )
        messagebox.showinfo("导出完成", f"CSV 明细已导出到:\n{out_dir}")

    def finish_ui(self, data):
        m_dps, sd_dps = data['m_dps'], data['sd_dps']
        dur, last_h = data['dur'], data['last_h']
        stats_pkg, log = data['stats_pkg'], data['log']
        dps_l, iters = data['dps_l'], data['iters']
        sim, gcds = data['sim_instance'], data['gcd_info']
        self.last_result_data = data
        self.last_report_metadata = self.build_report_metadata(
            sim, stats_pkg, dur, last_h, m_dps, sd_dps, iters, data.get("random_seed")
        )

        t = self.txt_res
        self.insert_report_header(t, self.last_report_metadata)
        t.insert(tk.END, "【面板与理论数据】\n", "h2")
        t.insert(tk.END, f"职业: {sim.job_profile.name} ({sim.job}) | 主属性({sim.job_profile.main_stat}): {sim.base_main} | 武器性能: {sim.stats['wd']} | 速度({sim.job_profile.speed_stat}): {sim.stats['sks']}\n")
        t.insert(tk.END, f"暴击: {sim.stats['crt']} -> {sim.crit_rate * 100:.3f}% (x{sim.crit_dmg:.3f})\n")
        t.insert(tk.END, f"直击: {sim.stats['dh']} -> {sim.dh_rate * 100:.3f}%\n")
        t.insert(tk.END, f"信念: {sim.stats['det']} | GCD(职业修正后): {gcds[1]:.3f}s (Base: {gcds[0]:.3f}s)\n")
        t.insert(tk.END, "-" * 50 + "\n\n")
        mode_str = "多Boss模式 (自动计算交集)" if sim.multi_boss_mode else "单模式 (读取文本框)"
        t.insert(tk.END, f"当前模式: {mode_str}\n")
        resource_warnings = stats_pkg.get('resource_warnings', [])
        if resource_warnings:
            t.insert(tk.END, f"资源合法性: {len(resource_warnings)} 条 warning，结果仅供趋势参考\n")
            for warning in resource_warnings[:12]:
                row_text = f"row {warning['row_no']} " if warning.get('row_no') is not None else ""
                t.insert(
                    tk.END,
                    f"  - {row_text}{warning['time']:.3f}s {warning['skill']}: {warning['message']}\n"
                )
            if len(resource_warnings) > 12:
                t.insert(tk.END, f"  - ... 另有 {len(resource_warnings) - 12} 条\n")
        else:
            t.insert(tk.END, "资源合法性: 未发现 warning\n")
        invalid_skill_events = stats_pkg.get("invalid_skill_events", [])
        if invalid_skill_events:
            t.insert(tk.END, f"无效技能: {len(invalid_skill_events)} 条不出伤/上天按不出记录\n")
            for item in invalid_skill_events[:12]:
                row_text = f"row {item['row_no']} " if item.get("row_no") is not None else ""
                t.insert(
                    tk.END,
                    f"  - {row_text}{float(item.get('time', 0.0)):.3f}s {item.get('skill', '-')}: {item.get('kind', '-')}\n"
                )
            if len(invalid_skill_events) > 12:
                t.insert(tk.END, f"  - ... 另有 {len(invalid_skill_events) - 12} 条\n")
        else:
            t.insert(tk.END, "无效技能: 未发现不出伤/上天按不出记录\n")
        t.insert(tk.END, f"最后技能出伤时间: {last_h:.3f}s\n")
        t.insert(tk.END, f"有效战斗时长: {dur:.3f}s\n")
        t.insert(tk.END, "-" * 50 + "\n")
        t.insert(tk.END, f"期望 DPS: {m_dps:,.2f} (σ = {sd_dps:,.2f})\n", "h1")
        max_dps = max(dps_l);
        min_dps = min(dps_l)
        t.insert(tk.END, f"最高 DPS: {max_dps:,.2f}\n");
        t.insert(tk.END, f"最低 DPS: {min_dps:,.2f}\n")

        t.insert(tk.END, "\n【极值预测 (基于正态分布)】\n", "h2")

        def p_norm(z):
            return m_dps + z * sd_dps

        t.insert(tk.END, f"Top 1%    (Z=2.326): {p_norm(2.326):,.2f}\n")
        t.insert(tk.END, f"Top 0.1%  (Z=3.090): {p_norm(3.090):,.2f}\n")
        t.insert(tk.END, f"Top 0.01% (Z=3.719): {p_norm(3.719):,.2f}\n")
        t.insert(tk.END, f"Bottom 1%          : {p_norm(-2.326):,.2f}\n")

        log.sort(key=lambda x: x['time'])
        for r in log:
            d_val = r['dmg'];
            d_str = f"{d_val}" if isinstance(d_val, str) else f"{d_val:.2f}"
            self.tree_log.insert("", tk.END,
                                 values=(f"{r['time']:.3f}", r['name'], r['potency'], r['buffs'], r['targets'],
                                         r['crit'], r['dh'], d_str))

        for detail in sorted(stats_pkg.get('dot_details', []), key=lambda row: (row.get('apply_time', 0), row.get('dot_id', 0))):
            last_tick_time = detail.get('last_tick_time')
            last_tick_text = "-" if last_tick_time is None else f"{float(last_tick_time):.3f}"
            damage_text = f"{float(detail.get('damage', 0.0)):,.2f}"
            target_id = detail.get('target_id', "-")
            target_text = f"T{target_id}" if target_id != "-" else "-"
            self.tree_dot_details.insert("", tk.END, values=(
                detail.get('dot_id', "-"),
                f"{float(detail.get('apply_time', 0.0)):.3f}",
                detail.get('source_name', "-"),
                detail.get('name', "-"),
                target_text,
                detail.get('potency', "-"),
                detail.get('ticks', 0),
                detail.get('missed_ticks', 0),
                damage_text,
                last_tick_text,
                detail.get('buffs_text', "-"),
            ))

        for row in stats_pkg.get("skill_variants", []):
            self.tree_skill_variants.insert("", tk.END, values=(
                row.get("skill", "-"),
                row.get("targets", 1),
                row.get("buffs", "-"),
                f"{float(row.get('effective_potency', 0.0)):.2f}",
                row.get("count", 0),
                row.get("potency_formula", "-"),
            ))

        s_dps = stats_pkg['dps'];
        s_cnt = stats_pkg['count']
        agg_cnt = stats_pkg['agg_count'];
        agg_crit = stats_pkg['agg_crit']
        agg_dh = stats_pkg['agg_dh'];
        agg_cdh = stats_pkg['agg_cdh']
        total_hits_list = stats_pkg['total_hits_list'];
        target_stats = stats_pkg.get('target_stats', {})

        for k in sorted(s_dps.keys(), key=lambda x: statistics.mean(s_dps[x]), reverse=True):
            ac = statistics.mean(s_cnt[k])
            total_hits = target_stats.get(k, 0);
            avg_t = total_hits / ac if ac > 0 else 1.0
            ad = statistics.mean(s_dps[k]);
            sd = statistics.stdev(s_dps[k]) if iters > 1 else 0
            th = agg_cnt[k]
            s_data = sim.get_skill(k)
            is_dmg_skill = (s_data is None) or (s_data.get('potency', 0) > 0) or (s_data.get('dot_potency', 0) > 0)
            if is_dmg_skill and th > 0:
                crit_str = f"{agg_crit[k] / th * 100:.1f}%"
                dh_str = f"{agg_dh[k] / th * 100:.1f}%"
                cdh_str = f"{agg_cdh[k] / th * 100:.1f}%"
            else:
                crit_str = "-"
                dh_str = "-"
                cdh_str = "-"
            if th > 0:
                crit_rate = agg_crit[k] / th * 100; dh_rate = agg_dh[k] / th * 100; cdh_rate = agg_cdh[k] / th * 100
            else:
                crit_rate = dh_rate = cdh_rate = 0.0
            self.tree_stats.insert("", tk.END, values=(
                k, f"{ac:.1f}", f"{avg_t:.1f}", f"{ad:.2f} ± {sd:.2f}",
                crit_str, dh_str, cdh_str
            ))

        avg_total_hits = statistics.mean(total_hits_list)
        std_total_hits = statistics.stdev(total_hits_list) if iters > 1 else 0
        self.tree_stats.insert("", tk.END, values=("--- TOTAL ---", f"{avg_total_hits:.1f} ± {std_total_hits:.1f}", "-",
                                                   f"{m_dps:.2f} ± {sd_dps:.2f}", "-", "-", "-"), tags=('total',))
        self.tree_stats.tag_configure('total', background='#4a90e2', foreground='white', font=("Segoe UI", 10, "bold"))

        # --- Fill Best Run Tab ---
        best_run = stats_pkg.get('best_run', {})
        if best_run:
            b_cnt = best_run['count'];
            b_dmg = best_run['dmg']
            b_crit = best_run['crit'];
            b_dh = best_run['dh'];
            b_cdh = best_run['cdh'];
            b_targets = best_run['targets']
            sorted_skills = sorted(b_dmg.keys(), key=lambda x: b_dmg[x], reverse=True)
            total_dmg_sum = 0
            for k in sorted_skills:
                c = b_cnt[k]
                if c <= 0: continue
                hits = b_targets[k];
                s_data = sim.get_skill(k)
                is_dmg_skill = (s_data is None) or (s_data.get('potency', 0) > 0) or (s_data.get('dot_potency', 0) > 0)
                if is_dmg_skill:
                    cr_str = f"{b_crit[k] / c * 100:.0f}%"
                    dr_str = f"{b_dh[k] / c * 100:.0f}%"
                    cdr_str = f"{b_cdh[k] / c * 100:.0f}%"
                else:
                    cr_str = "-"
                    dr_str = "-"
                    cdr_str = "-"
                d = b_dmg[k];
                total_dmg_sum += d
                cr = b_crit[k] / c * 100;
                dr = b_dh[k] / c * 100;
                cdr = b_cdh[k] / c * 100
                self.tree_best.insert("", tk.END, values=(k, c, hits, f"{d:,.0f}", cr_str, dr_str, cdr_str))

            self.tree_best.insert("", tk.END,
                                  values=("--- MAX RUN TOTAL ---", "-", "-", f"{total_dmg_sum:,.0f}", "-", "-", "-"),
                                  tags=('total',))
            self.tree_best.tag_configure('total', background='#e67e22', foreground='white',
                                         font=("Segoe UI", 10, "bold"))

        interval_data = stats_pkg.get('interval_data', {})
        if interval_data:
            sorted_times = sorted(interval_data.keys())
            for t_point in sorted_times:
                dmgs = interval_data[t_point]
                if not dmgs: continue

                # 1. 计算该节点的有效战斗时间 (扣除上天)
                eff_duration = sim.get_effective_duration(t_point)

                # 2. 计算 1000 次模拟在该节点的 RD (累计伤害 / 有效时间)
                rds = [d / eff_duration for d in dmgs]

                # 3. 计算统计数据
                mean_rd = statistics.mean(rds)
                std_rd = statistics.stdev(rds) if len(rds) > 1 else 0
                max_rd = max(rds)

                # 4. 计算水位线 (基于正态分布公式)
                top1 = mean_rd + 2.326 * std_rd  # Top 1%
                top01 = mean_rd + 3.090 * std_rd  # Top 0.1%

                # 5. 格式化时间并插入表格
                mins = int(t_point // 60)
                secs = t_point % 60
                # 如果是整数秒则显示 0:15，如果是小数秒则显示 0:15.5
                if t_point % 1 == 0:
                    time_str = f"{mins}:{int(secs):02d}"
                else:
                    time_str = f"{mins}:{secs:04.1f}"

                self.tree_intervals.insert("", tk.END, values=(
                    time_str,
                    f"{mean_rd:,.2f} ± {std_rd:,.2f}",  # 期望 ± 标准差
                    f"{max_rd:,.2f}",  # 极值(最大值)
                    f"{top1:,.2f}",  # Top 1%
                    f"{top01:,.2f}"  # Top 0.1%
                ))


        bk = defaultdict(int);

        step = 100
        for d in dps_l: bk[math.floor(d / step) * step] += 1
        if bk:
            min_b, max_b = min(bk), max(bk)
            for b in range(min_b, max_b + step, step):
                count = bk[b]
                if count > 0:
                    count_ge = sum(c for k, c in bk.items() if k >= b);
                    pct_ge = count_ge / iters * 100
                    self.tree_dist.insert("", tk.END, values=(f"{b}-{b + step}", count, f"{pct_ge:.2f}%"))

        if HAS_MATPLOTLIB: self.draw_plot(dps_l, m_dps, sd_dps)
        self.btn_run.config(state="normal", text="▶ 运行模拟");
        messagebox.showinfo("模拟完成噜", "看看这把roll得怎么样！")

        high_runs = stats_pkg.get('high_rd_runs', {})
        if high_runs:
            t.insert(tk.END, f"\n有 {len(high_runs)} 次模拟的 RD 超过了设定阈值！\n", "h2")

            # 关键修改 1：把按钮的“老爹”从 tab 改为 t (也就是滚动文本框本身)
            btn_view_high = ttk.Button(t, text="📈 点击查看高 RD 模拟详情与曲线",
                                       command=lambda: self.show_high_rd_window(high_runs, sim))

            # 关键修改 2：使用 window_create 魔法，把按钮当成一个“文字”直接塞进文本框的末尾！
            t.window_create(tk.END, window=btn_view_high)
            t.insert(tk.END, "\n\n")  # 补充两个换行让排版更好看

    def draw_plot(self, data, mean, std):
        fig = Figure(figsize=(8, 5), dpi=100, facecolor='#2b2b2b');
        ax = fig.add_subplot(111);
        ax.set_facecolor('#1e1e1e')
        min_val = math.floor(min(data) / 100) * 100;
        max_val = math.ceil(max(data) / 100) * 100
        bins_arr = np.arange(min_val, max_val + 100, 100);
        weights = np.ones(len(data)) / len(data) * 100
        n, _, patches = ax.hist(data, bins=bins_arr, weights=weights, alpha=0.7, color='#4a90e2', edgecolor='#1e1e1e')
        if std > 1e-9:
            xmin, xmax = ax.get_xlim();
            x = np.linspace(xmin, xmax, 200)
            pdf = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2);
            y_curve = pdf * 100 * 100
            ax.plot(x, y_curve, 'w', linewidth=2, label='Normal Distribution')
            colors = {'1%': '#f1c40f', '0.1%': '#e67e22', '0.01%': '#e74c3c'}
            z_scores = [(2.326, '1%'), (3.090, '0.1%'), (3.719, '0.01%')]
            for z, label in z_scores:
                val = mean + z * std;
                ax.axvline(val, color=colors[label], linestyle='--', alpha=0.8, label=f'Top {label}')
        else:
            ax.axvline(mean, color='white', linestyle='-', alpha=0.8, label='Mean')
        ax.set_title(f"DPS Distribution (N={len(data)}, Bin=100)", color='white')
        ax.set_xlabel("DPS", color='white');
        ax.set_ylabel("Frequency (Probability %)", color='white')
        ax.tick_params(colors='white')
        for spine in ax.spines.values(): spine.set_edgecolor('white')
        ax.legend(facecolor='#3c3f41', edgecolor='white', labelcolor='white')
        canvas = FigureCanvasTkAgg(fig, master=self.frame_plot);
        canvas.draw();
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def show_high_rd_window(self, high_rd_runs, sim_instance):
        win = tk.Toplevel(self.root)
        win.title("高 RD 模拟详情 (超过阈值)")
        win.geometry("900x700")
        win.configure(bg=self.colors["bg"])

        try:
            for icon_name in ("FFXIV_SIM.ico", "XIV_SIM.ico", "ffxiv_ndps.ico"):
                ico_path = resource_path(icon_name)
                if os.path.exists(ico_path):
                    win.iconbitmap(ico_path)
                    break
        except Exception:
            # 如果加载失败（例如文件丢失），程序将保持默认图标并继续运行
            pass
        
        # 左侧列表
        left_fr = ttk.Frame(win, width=250)
        left_fr.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(left_fr, text="符合条件的模拟编号", font=("Segoe UI", 11, "bold")).pack(pady=5)

        cols = ("run_id", "rd")
        tree = ttk.Treeview(left_fr, columns=cols, show="headings", height=25)
        tree.heading("run_id", text="模拟编号")
        tree.column("run_id", width=80, anchor="center")
        tree.heading("rd", text="最终 RD")
        tree.column("rd", width=120, anchor="center")
        tree.pack(fill=tk.BOTH, expand=True)

        for rid in sorted(high_rd_runs.keys(), key=lambda x: high_rd_runs[x]['rd'], reverse=True):
            tree.insert("", tk.END, values=(rid, f"{high_rd_runs[rid]['rd']:,.2f}"))

        # 右侧绘图区域
        right_fr = ttk.Frame(win)
        right_fr.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ctrl_fr = ttk.Frame(right_fr)
        ctrl_fr.pack(fill=tk.X, pady=5)

        ttk.Label(ctrl_fr, text="输入编号查看曲线:").pack(side=tk.LEFT)
        entry_id = ttk.Entry(ctrl_fr, width=15)
        entry_id.pack(side=tk.LEFT, padx=5)

        plot_fr = ttk.Frame(right_fr)
        plot_fr.pack(fill=tk.BOTH, expand=True)

        def draw_curve():
            target_id = entry_id.get().strip()
            if not target_id.isdigit() or int(target_id) not in high_rd_runs:
                messagebox.showwarning("错误", "找不到该模拟编号！", parent=win)
                return

            run_data = high_rd_runs[int(target_id)]
            history = run_data['history']

            # 计算平滑的累计 RD 曲线数据
            times = sorted(history.keys())
            rds = []
            valid_times = []

            for t in times:
                eff_duration = sim_instance.get_effective_duration(t)
                # 累计RD = 截至该2秒节点的总伤害 / 截至该节点的有效时间
                rds.append(history[t] / eff_duration)
                valid_times.append(t)

            for widget in plot_fr.winfo_children():
                widget.destroy()

            fig = Figure(figsize=(8, 5), dpi=100, facecolor='#2b2b2b')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1e1e1e')

            # 绘制曲线
            line, = ax.plot(valid_times, rds, color='#4a90e2', linewidth=2, linestyle='-')
            ax.set_title(f"Run #{target_id} RD Timeline (Final RD: {run_data['rd']:,.2f})", color='white')
            ax.set_xlabel("Time (s)", color='white')
            ax.set_ylabel("Cumulative RD", color='white')
            ax.tick_params(colors='white')
            for spine in ax.spines.values(): spine.set_edgecolor('white')

            # 创建悬停标注点 (Tooltip)
            annot = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                bbox=dict(boxstyle="round4,pad=0.5", fc="#3c3f41", ec="#4a90e2", lw=1),
                                color="white", arrowprops=dict(arrowstyle="->", color="#4a90e2"))
            annot.set_visible(False)

            # 悬停事件逻辑
            def hover(event):
                if event.inaxes == ax:
                    # 寻找距离鼠标 X 轴最近的数据点
                    x_mouse = event.xdata
                    if x_mouse is None: return

                    # 找到最近的时间点索引
                    idx = min(range(len(valid_times)), key=lambda i: abs(valid_times[i] - x_mouse))

                    x_closest = valid_times[idx]
                    y_closest = rds[idx]

                    annot.xy = (x_closest, y_closest)
                    mins = int(x_closest // 60)
                    secs = int(x_closest % 60)
                    annot.set_text(f"Time: {mins}:{secs:02d}\nRD: {y_closest:,.2f}")
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", hover)

            canvas = FigureCanvasTkAgg(fig, master=plot_fr)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ttk.Button(ctrl_fr, text="📊 绘制平滑曲线", command=draw_curve).pack(side=tk.LEFT)

        # 允许双击左侧列表直接绘制
        def on_tree_double_click(event):
            selection = tree.selection()
            if selection:
                run_id = tree.item(selection[0], "values")[0]
                entry_id.delete(0, tk.END)
                entry_id.insert(0, run_id)
                draw_curve()

        tree.bind("<Double-1>", on_tree_double_click)


SamuraiApp = DpsSimulatorApp


def main(argv=None):
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--self-test", action="store_true", help="run packaged resource and simulator smoke tests")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = tk.Tk()
    root.configure(bg="#2b2b2b")
    DpsSimulatorApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
