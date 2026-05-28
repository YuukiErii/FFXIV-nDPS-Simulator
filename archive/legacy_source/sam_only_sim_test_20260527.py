import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import math
import random
import statistics
import csv
import threading
import heapq
import ctypes
from collections import deque, Counter, defaultdict
import os
import sys
import json
from itertools import count

# 尝试导入 matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def resource_path(relative_path):
    """ 获取资源绝对路径，适配 PyInstaller 打包后的临时目录 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ==========================================
# 1. 全局配置与技能库
# ==========================================
AA_POTENCY = 90
AA_DELAY = 0.53
TINCTURE_STR = 432
TINCTURE_DELAY = 0.64
SLIDECAST_WINDOW = 0.5  # 滑步窗口时间

SKILL_DB = {
    "晓风": {"cast": 0, "delay": 0.85, "potency": 240, "base_potency": 240},
    "燕飞": {"cast": 0, "delay": 0.71, "potency": 100, "base_potency": 100},
    "阵风": {"cast": 0, "delay": 0.62, "potency": 300, "base_potency": 140, "combo_prev": ["晓风"],
             "grants": "fugetsu"},
    "士风": {"cast": 0, "delay": 0.80, "potency": 300, "base_potency": 140, "combo_prev": ["晓风"], "grants": "shifu"},
    "月光": {"cast": 0, "delay": 0.76, "potency": 420, "base_potency": 200, "combo_prev": ["阵风"],
             "meikyo_grants": "fugetsu"},
    "花车": {"cast": 0, "delay": 0.62, "potency": 420, "base_potency": 200, "combo_prev": ["士风"],
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
    "天道五剑": {"cast": 1.3, "delay": 0.62, "potency": 300, "is_aoe": True, "decay": 0},
    "天道回返五剑": {"cast": 0, "delay": 0.62, "potency": 300, "is_aoe": True, "decay": 0},
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


# ==========================================
# 2. 模拟核心
# ==========================================
class SamuraiSimulator:
    def __init__(self, stats, timeline_data, downtime_config=None, dot_config=None,
                 multi_boss_mode=False, global_downtime_list=None, iterations=1000, custom_snaps=None):
        self.stats = stats
        self.timeline_data = timeline_data
        self.custom_snaps = custom_snaps if custom_snaps else []
        self.multi_boss_mode = multi_boss_mode
        self.downtime_config = downtime_config if downtime_config else {}
        self.global_downtime_list = global_downtime_list if global_downtime_list else []
        self.dot_config = dot_config if dot_config else {}
        self.iterations = iterations

        self.lvl_main = 440;
        self.lvl_sub = 420;
        self.lvl_div = 2780;
        self.lvl_ap = 237
        self.party_bonus = stats['party_bonus']
        self.base_str = stats['str']

        self.crit_rate = math.floor(200 * (stats['crt'] - self.lvl_sub) / self.lvl_div + 50) / 1000
        self.crit_dmg = math.floor(200 * (stats['crt'] - self.lvl_sub) / self.lvl_div + 1400) / 1000
        self.dh_rate = math.floor(550 * (stats['dh'] - self.lvl_sub) / self.lvl_div) / 1000
        self.dh_dmg = 1.25
        self.det_mult = math.floor(140 * (stats['det'] - self.lvl_main) / self.lvl_div + 1000) / 1000
        self.spd_mult = math.floor(130 * (stats['sks'] - self.lvl_sub) / self.lvl_div + 1000) / 1000

        wd_job_mod = math.floor(self.lvl_main * 112 / 1000)
        self.f_auto = math.floor((wd_job_mod + stats['wd']) * (stats['delay'] / 3.00))
        self.wd_factor = (stats['wd'] + wd_job_mod) / 100

        self.ap_val_normal = self._calc_ap(False)
        self.ap_val_potion = self._calc_ap(True)

    def _calc_ap(self, has_potion):
        current_str = self.base_str + (TINCTURE_STR if has_potion else 0)
        eff_str = math.floor(current_str * self.party_bonus)
        return math.floor(self.lvl_ap * (eff_str - self.lvl_main) / self.lvl_main + 100)

    @staticmethod
    def calculate_gcd(sks):
        lvl_sub = 420;
        lvl_div = 2780
        speed_val = math.floor(130 * (sks - lvl_sub) / lvl_div)
        base_ms = math.floor((1000 - speed_val) * 2500 / 1000)
        shifu_ms = math.floor(base_ms * 0.87)
        return base_ms / 1000.0, shifu_ms / 1000.0

    def calculate_damage_val(self, potency, is_auto=False, is_dot=False, active_buffs=None, guaranteed_crit=False,
                             has_potion=False):
        if active_buffs is None: active_buffs = {}
        ap_val = self.ap_val_potion if has_potion else self.ap_val_normal
        base = potency * (ap_val / 100.0) * self.det_mult

        if active_buffs.get('fugetsu'): base *= 1.13
        if is_auto:
            base = base * self.spd_mult * (self.f_auto / 100.0)
        elif is_dot:
            base = base * self.spd_mult * self.wd_factor
        else:
            base = base * self.wd_factor

        is_crit = True if guaranteed_crit else (random.random() < self.crit_rate)
        is_dh = random.random() < self.dh_rate
        val = base * self.crit_dmg if is_crit else base
        if is_dh: val *= self.dh_dmg
        return val * random.uniform(0.95, 1.05), is_crit, is_dh

    # 判定特定目标是否在指定时间点不可选中
    def is_target_untargetable(self, t, tid):
        if not self.multi_boss_mode: return False
        if tid not in self.downtime_config: return False
        for s, e in self.downtime_config[tid]:
            if s + 1e-9 < t < e - 1e-9: return True
        return False

    # 判定全局上天 (用于单Boss模式 或 普攻暂停)
    def is_global_downtime(self, t):
        for s, e in self.global_downtime_list:
            if s + 1e-9 < t < e - 1e-9: return True
        return False

    def get_effective_downtime_total(self, end_time):
        total = 0
        for s, e in self.global_downtime_list:
            if s < end_time:
                actual_end = min(e, end_time)
                if actual_end > s: total += (actual_end - s)
        return total

    def run_one_simulation(self, is_first_run=False):
        pq = []
        tie_breaker = count()
        for t, name, target_count in self.timeline_data:
            heapq.heappush(pq, (t, 0, 'press', next(tie_breaker), {'name': name, 'targets': target_count}))
        heapq.heappush(pq, (random.uniform(0.0, 3.0), 2, 'tick', next(tie_breaker), None))

        last_skill_hit_time = 0.0
        for t, name, _ in reversed(self.timeline_data):
            s = SKILL_DB.get(name)
            if s and (s.get('potency', 0) > 0 or s.get('dot_potency', 0) > 0):
                cast, delay = s.get('cast', 0), s.get('delay', 0.5)
                last_skill_hit_time = t + cast + delay
                break
        if last_skill_hit_time == 0 and self.timeline_data:
            last_skill_hit_time = self.timeline_data[-1][0]

        run_snapshots = {}  # 用于存储本次运行的快照数据 {time: current_damage}
        cp_time = 30.0
        while cp_time < last_skill_hit_time:
            heapq.heappush(pq, (cp_time, 5, 'snapshot', next(tie_breaker), {'snap_time': cp_time}))
            cp_time += 120.0
        all_custom_snaps = set(self.custom_snaps)
        for ct in all_custom_snaps:
            if 0 < ct <= last_skill_hit_time:
                heapq.heappush(pq, (ct, 5, 'snapshot', next(tie_breaker), {'snap_time': ct}))

        history_snapshots = {}
        ht_time = 2.0
        while ht_time <= last_skill_hit_time:
            heapq.heappush(pq, (ht_time, 5, 'history_tick', next(tie_breaker), {'snap_time': ht_time}))
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

        buffs = {'fugetsu': -1.0, 'shifu': -1.0, 'meikyo': 0}
        meikyo_expire = -1.0;
        combo_action = None;
        combo_time = -1.0
        active_dots = [];
        casting_state = (-1, -1, -1);
        potion_active_until = -1.0
        aa_running = False;
        next_aa_timestamp = 0.0

        # 技能计数移到外面，确保 press 和 damage 共享
        # 但为了避免 press 失败导致计数错乱，我们采用 "尝试计数" 和 "成功计数"
        # 实际上，FF14 中如果读条中断，该技能不算使用。
        # 我们在这里维护一个 "准备按下的计数器" 用来查找 Config
        skill_attempt_counter = Counter()
        combat_log = []

        while pq:
            t, _, ev_type, _, payload = heapq.heappop(pq)
            if t > last_skill_hit_time + 0.001: break
            current_time = t
            global_dt = self.is_global_downtime(current_time)

            if ev_type == 'snapshot':
                snap_t = payload['snap_time']
                run_snapshots[snap_t] = total_damage
                continue  # 处理完直接进行下一个循环

            if ev_type == 'history_tick':
                snap_t = payload['snap_time']
                history_snapshots[snap_t] = total_damage
                continue

            if ev_type == 'press':
                name = payload['name'];
                target_count = payload['targets']
                skill = SKILL_DB.get(name)
                if not skill: continue

                # --- 1. 准备工作：计数器与快照时间计算 ---
                current_attempt_idx = skill_attempt_counter[name]
                skill_attempt_counter[name] += 1

                # 计算快照时间 (用于判定此时Boss是否在场)
                # 读条技能看滑步点，瞬发技能看当前
                cast_time = skill.get('cast', 0)
                snapshot_time = current_time
                if cast_time > 0:
                    snapshot_time = current_time + cast_time - SLIDECAST_WINDOW
                    if snapshot_time < current_time: snapshot_time = current_time

                # --- 2. 确定 Target ID (智能索敌逻辑) ---
                target_id = 1  # 默认打 Target 1
                is_manual_target = False

                is_enpi_enhanced = False  # 默认为普通版

                # 1. 如果按下的是“必杀剑·夜天”，获得 15s Buff
                if name == "必杀剑·夜天":
                    buffs['enhanced_enpi'] = current_time + 15.0

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

                # --- 3. 最终有效性判定 ---
                # 拿到最终的 target_id 后，再次检查该目标在快照点是否上天
                # 如果是单模式，检查全局上天

                is_buff_skill = (skill.get('potency', 0) == 0 and skill.get('dot_potency', 0) == 0)
                is_snapshot_invalid = False
                if not is_buff_skill:
                    if self.multi_boss_mode:
                        if self.is_target_untargetable(snapshot_time, target_id):
                            is_snapshot_invalid = True
                    else:
                        if self.is_global_downtime(snapshot_time):
                            is_snapshot_invalid = True

                # 如果判定无效（没打出去/读条中断），记录日志并跳过
                if is_snapshot_invalid:
                    if is_first_run:
                        combat_log.append({
                            'time': current_time, 'name': name, 'potency': '-',
                            'buffs': 'Interrupted', 'crit': '-', 'dh': '-',
                            'dmg': f'0 (T{target_id}不在场)', 'targets': '-'
                        })
                    continue

                    # --- 4. 技能成功释放 (入队后续事件) ---
                if not aa_running and not global_dt and current_time >= 0.0:
                    aa_running = True;
                    next_aa_timestamp = current_time
                    heapq.heappush(pq,
                                   (current_time, 1, 'aa_check', next(tie_breaker), {'scheduled_time': current_time}))

                if name == "爆发药":
                    potion_active_until = current_time + TINCTURE_DELAY + 30.0
                    if is_first_run:
                        combat_log.append(
                            {'time': current_time, 'name': '[爆发药]', 'potency': '-', 'buffs': '(Dur 30s)',
                             'crit': '-', 'dh': '-', 'dmg': '-', 'targets': 1})
                    continue

                if name == "燕飞":
                    # 检查 Buff 是否有效
                    if buffs.get('enhanced_enpi', -1.0) > snapshot_time:
                        is_enpi_enhanced = True
                        # 消耗 Buff (设为过期)
                        buffs['enhanced_enpi'] = -1.0

                cast, delay = skill.get('cast', 0), skill.get('delay', 0.5)
                hit_time = current_time + cast + delay
                check_time = current_time

                if cast > 0:
                    check_time = current_time + cast - 0.5
                    casting_state = (current_time, current_time + cast, check_time)
                    if aa_running and next_aa_timestamp > current_time:
                        penalty = cast - 0.5;
                        next_aa_timestamp += penalty
                        heapq.heappush(pq, (next_aa_timestamp, 1, 'aa_check', next(tie_breaker),
                                            {'scheduled_time': next_aa_timestamp}))

                is_potion = (potion_active_until > check_time >= (potion_active_until - 30.0))
                is_meikyo_proc = False
                if buffs['meikyo'] > 0 and meikyo_expire > current_time:
                    if skill.get('combo_prev') or name in ['雪风', '月光', '花车', '晓风']:
                        buffs['meikyo'] -= 1;
                        is_meikyo_proc = True

                # 关键：将智能判定后的 target_id 传给 damage 事件
                heapq.heappush(pq, (hit_time, 3, 'damage', next(tie_breaker), {
                    'name': name,
                    'meikyo': is_meikyo_proc,
                    'has_potion': is_potion,
                    'targets': target_count,
                    'tid': target_id,
                    'enhanced': is_enpi_enhanced  # <--- 新增传入这个参数
                }))

                if name == '明镜止水':
                    buffs['meikyo'] = 3;
                    meikyo_expire = current_time + 20.0

            elif ev_type == 'damage':
                name = payload['name'];
                is_meikyo = payload['meikyo']
                has_potion = payload['has_potion'];
                target_count = payload['targets']
                target_id = payload['tid']  # 从 press 传过来

                skill = SKILL_DB.get(name)
                skill_count_map[name] += 1

                is_enhanced = payload.get('enhanced', False)

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

                active_buffs = {'fugetsu': buffs['fugetsu'] > current_time}
                is_combo = is_meikyo
                if not is_combo and 'combo_prev' in skill:
                    if combo_action in skill['combo_prev'] and (current_time - combo_time < 30): is_combo = True
                potency = skill['potency']
                if 'base_potency' in skill and not is_combo: potency = skill['base_potency']

                is_aoe_skill = skill.get('is_aoe', False);
                decay_rate = skill.get('decay', 0.0)
                step_total_damage = 0;
                main_crit = False;
                main_dh = False

                skill = SKILL_DB.get(name)

                potency = skill['potency']

                if name == "燕飞" and is_enhanced:
                    potency = skill.get('enhanced_potency', 270)
                    # ==================================

                if 'base_potency' in skill and not is_combo and name != "燕飞":
                    # 注意：燕飞没有连击概念，只有 Buff 概念，所以排除它
                    potency = skill['base_potency']


                # 如果没上天，计算伤害
                if not is_damage_immune:
                    for i in range(target_count):
                        modifier = 1.0
                        if is_aoe_skill and i > 0: modifier = 1.0 - decay_rate
                        dmg_val, is_c, is_d = self.calculate_damage_val(potency, is_auto=False,
                                                                        active_buffs=active_buffs,
                                                                        guaranteed_crit=skill.get('guaranteed_crit',
                                                                                                  False),
                                                                        has_potion=has_potion)
                        step_total_damage += (dmg_val * modifier)
                        if i == 0: main_crit = is_c; main_dh = is_d

                # 如果上天了，step_total_damage 为 0



                total_damage += step_total_damage
                skill_dmg_map[name] += step_total_damage
                if main_crit: skill_crit_map[name] += 1
                if main_dh: skill_dh_map[name] += 1
                if main_crit and main_dh: skill_cdh_map[name] += 1

                # --- DoT 挂载 ---
                # 只要进入了 damage 阶段（说明 press 阶段快照判定通过了）
                # 即使当前出伤是 0 (免疫)，DoT 依然会挂在目标身上
                # 之后的 tick 事件会负责判断每一跳是否有伤害
                if 'dot_potency' in skill:
                    if self.multi_boss_mode:
                        active_dots = [d for d in active_dots if not (d['name'] == name and d['tid'] == target_id)]
                    else:
                        active_dots = [d for d in active_dots if d['name'] != name]

                    active_dots.append({'name': name, 'tid': target_id, 'potency': skill['dot_potency'],
                                        'buffs': active_buffs, 'expire': current_time + skill['dot_duration'],
                                        'has_potion': has_potion})

                if is_first_run and potency > 0:
                    b_list = []
                    if active_buffs.get('fugetsu'): b_list.append("风月")
                    if has_potion: b_list.append("药")

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
                        'buffs': "+".join(b_list) if b_list else "-",
                        'crit': c_str, 'dh': d_str,
                        'dmg': dmg_str, 'targets': target_count
                    })

                grant = None
                if is_combo and skill.get('grants'): grant = skill['grants']
                if is_meikyo and skill.get('meikyo_grants'): grant = skill['meikyo_grants']
                if grant: buffs[grant] = current_time + 40.0
                if skill.get('combo_prev') or name == "晓风":
                    if name == "晓风":
                        combo_action = "晓风"
                    elif is_combo and name == "阵风":
                        combo_action = "阵风"
                    elif is_combo and name == "士风":
                        combo_action = "士风"
                    elif is_combo:
                        combo_action = None
                    combo_time = current_time

            elif ev_type == 'aa_check':
                if abs(payload['scheduled_time'] - next_aa_timestamp) > 0.0001: continue
                if self.is_global_downtime(current_time):
                    aa_running = False;
                    continue
                c_start, c_end, c_slide = casting_state

                is_potion = (potion_active_until > current_time)
                is_fugetsu = (buffs['fugetsu'] > current_time)
                heapq.heappush(pq, (current_time + AA_DELAY, 3, 'aa_damage', next(tie_breaker),
                                    {'has_potion': is_potion, 'has_fugetsu': is_fugetsu}))
                has_shifu = buffs['shifu'] > current_time
                interval = self.stats['delay'] * (0.87 if has_shifu else 1.0)
                next_aa_timestamp = current_time + interval
                heapq.heappush(pq, (next_aa_timestamp, 1, 'aa_check', next(tie_breaker),
                                    {'scheduled_time': next_aa_timestamp}))

            elif ev_type == 'aa_damage':
                if not self.is_global_downtime(current_time):
                    d = payload
                    skill_count_map['Auto Attack'] += 1;
                    skill_target_sum_map['Auto Attack'] += 1;
                    total_hits_in_run += 1
                    dmg, is_c, is_d = self.calculate_damage_val(AA_POTENCY, is_auto=True,
                                                                active_buffs={'fugetsu': d['has_fugetsu']},
                                                                has_potion=d['has_potion'])
                    total_damage += dmg
                    skill_dmg_map['Auto Attack'] += dmg
                    if is_c: skill_crit_map['Auto Attack'] += 1
                    if is_d: skill_dh_map['Auto Attack'] += 1
                    if is_c and is_d: skill_cdh_map['Auto Attack'] += 1
                    if is_first_run:
                        b_list = []
                        if d['has_fugetsu']: b_list.append("风月")
                        if d['has_potion']: b_list.append("药")
                        combat_log.append({'time': current_time, 'name': 'Auto Attack', 'potency': AA_POTENCY,
                                           'buffs': "+".join(b_list) if b_list else "-", 'crit': "✔" if is_c else "",
                                           'dh': "✔" if is_d else "", 'dmg': dmg, 'targets': 1})

            elif ev_type == 'tick':
                temp_active_dots = []
                for dot in active_dots:
                    if dot['expire'] < current_time: continue
                    temp_active_dots.append(dot)
                    if self.multi_boss_mode:
                        if self.is_target_untargetable(current_time, dot['tid']): continue
                    else:
                        if self.is_global_downtime(current_time): continue

                    skill_count_map['Dot Tick'] += 1;
                    skill_target_sum_map['Dot Tick'] += 1;
                    total_hits_in_run += 1
                    dmg, is_c, is_d = self.calculate_damage_val(dot['potency'], is_dot=True, active_buffs=dot['buffs'],
                                                                has_potion=dot['has_potion'])
                    total_damage += dmg
                    skill_dmg_map['Dot Tick'] += dmg
                    if is_c: skill_crit_map['Dot Tick'] += 1
                    if is_d: skill_dh_map['Dot Tick'] += 1
                    if is_c and is_d: skill_cdh_map['Dot Tick'] += 1
                    if is_first_run:
                        b_list = []
                        if dot['buffs'].get('fugetsu'): b_list.append("风月")
                        if dot['has_potion']: b_list.append("药")
                        t_lbl = f"DoT(T{dot['tid']})" if self.multi_boss_mode else "DoT"
                        combat_log.append({'time': current_time, 'name': '彼岸花 (Dot)', 'potency': dot['potency'],
                                           'buffs': "+".join(b_list) if b_list else "-", 'crit': "✔" if is_c else "",
                                           'dh': "✔" if is_d else "", 'dmg': dmg, 'targets': t_lbl})
                active_dots = temp_active_dots
                heapq.heappush(pq, (current_time + 3.0, 2, 'tick', next(tie_breaker), None))

        return (total_damage, last_skill_hit_time, skill_dmg_map, skill_count_map, skill_crit_map, skill_dh_map,
                skill_cdh_map, total_hits_in_run, combat_log, skill_target_sum_map, run_snapshots, history_snapshots)

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
                dmg, lh, s_dmg, s_cnt, s_crit, s_dh, s_cdh, tot_hits, log, s_targets, r_snaps, h_snaps = self.run_one_simulation(is_first)
                if is_first:
                    first_log = log
                    self.target_stats_snapshot = s_targets

                for st, sd in r_snaps.items():
                    agg_snapshots[st].append(sd)

                dt_loss = self.get_effective_downtime_total(lh)
                dur = max(1, lh - dt_loss)
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
            'high_rd_runs': high_rd_runs
        }
        return dps_list, sim_dur, last_hit, stats_pkg, first_log


# ==========================================
# 3. UI (Frontend)
# ==========================================
class SamuraiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FF14 Samurai DPS Simulator")
        self.root.geometry("1400x950")

        try:
            myappid = 'hyxz.ff14.samurai.sim.v3'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        try:
            png_path = resource_path("SAM.png")
            if os.path.exists(png_path):
                img = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, img)
            else:
                ico_path = resource_path("ffxiv_ndps.ico")
                if os.path.exists(ico_path):
                    self.root.iconbitmap(ico_path)
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

        ttk.Label(main_container, text="XIV SIM by hyxz (Multi-targets compatible)", style="Header.TLabel").pack(anchor="w",
                                                                                                            pady=(0,
                                                                                                                  10))

        ctrl_fr = ttk.Frame(main_container);
        ctrl_fr.pack(fill=tk.X)
        left = ttk.Frame(ctrl_fr);
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        s_fr = ttk.LabelFrame(left, text=" 属性 ", padding=10);
        s_fr.pack(fill=tk.BOTH, expand=True)
        self.ents = {}
        defs = {"力量 (STR)": "6498", "暴击 (CRT)": "3605", "信念 (DET)": "2426", "直击 (DHT)": "1793",
                "技速 (SKS)": "689", "武器性能": "158", "攻击间隔": "2.64", "队伍加成": "1.05", "模拟次数": "10000", "RD筛选阈值": "46000"}
        r = 0
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
        self.user_dot_config = {};
        self.user_downtime_config = defaultdict(list)

        ttk.Button(b_box, text="1. 导入轴 (CSV)", command=self.load_csv).pack(side=tk.LEFT)
        ttk.Button(b_box, text="2. 导入目标 (TXT)", command=self.load_txt).pack(side=tk.LEFT, padx=5)
        ttk.Button(b_box, text="3. 配置 DoT与上天", command=self.open_dot_config).pack(side=tk.LEFT, padx=5)
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

        self.nb = ttk.Notebook(main_container);
        self.nb.pack(fill=tk.BOTH, expand=True)

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

        self.tab_stats = ttk.Frame(self.nb);
        self.nb.add(self.tab_stats, text="技能详情 (平均)")
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

    def load_csv(self):
        p = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not p: return
        self.csv_path = p
        self.process_files()

    def load_txt(self):
        p = filedialog.askopenfilename(filetypes=[("Text/JSON", "*.txt")])
        if not p: return
        self.txt_path = p
        self.process_files()

    def process_files(self):
        csv_name = os.path.basename(self.csv_path) if self.csv_path else "未加载"
        txt_name = os.path.basename(self.txt_path) if self.txt_path else "未加载"

        if self.csv_path and self.txt_path:
            self.lbl_st.config(text=f"CSV: {csv_name} | TXT: {txt_name}", foreground="#98c379")
        elif self.csv_path:
            self.lbl_st.config(text=f"CSV: {csv_name} | TXT: (单目标模式)", foreground="#e5c07b")
        else:
            self.lbl_st.config(text="等待导入...", foreground="#aaaaaa")
            return

        try:
            temp_csv = []
            with open(self.csv_path, encoding='utf-8-sig') as f:
                rd = csv.reader(f)
                if csv.Sniffer().has_header(f.read(1024)):
                    f.seek(0); next(rd)
                else:
                    f.seek(0)
                for r in rd:
                    if len(r) >= 2: temp_csv.append({'time': float(r[0]), 'name': r[1].strip()})

            txt_skills = []
            if self.txt_path:
                with open(self.txt_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    txt_skills = [x for x in log_data['actions'] if x['type'] == 'Skill']

            final_loaded = []
            txt_idx = 0;
            max_txt = len(txt_skills);
            search_window = 15
            for row in temp_csv:
                raw_name = row['name'];
                cn_name = SKILL_TRANSLATION.get(raw_name, raw_name);
                target_count = 1
                if txt_skills:
                    for i in range(txt_idx, min(txt_idx + search_window, max_txt)):
                        txt_item = txt_skills[i];
                        txt_n = txt_item.get('skillName', "")
                        if (raw_name.lower() in txt_n.lower()) or (txt_n.lower() in raw_name.lower()):
                            # === 修改开始：适配 targetList 格式 ===
                            if 'targetList' in txt_item:
                                # 如果有 targetList，目标数 = 列表长度
                                target_count = len(txt_item['targetList'])
                            else:
                                # 兼容旧格式
                                target_count = txt_item.get('targetCount', 1)
                            # === 修改结束 ===

                            txt_idx = i + 1;

                            break
                final_loaded.append((row['time'], cn_name, int(target_count)))
            self.loaded = final_loaded
        except Exception as e:
            messagebox.showerror("处理错误", f"解析文件失败:\n{str(e)}")
            self.loaded = []

    def open_dot_config(self):
        if not self.loaded: messagebox.showwarning("提示", "请先导入技能轴！"); return
        dot_skills = ["彼岸花"];
        found_dots = [];
        counts = defaultdict(int);
        max_target_id = 1
        for t, name, c in self.loaded:
            if c > max_target_id: max_target_id = c
        for t, name, _ in self.loaded:
            if name in dot_skills:
                idx = counts[name];
                current_tid = 1
                if name in self.user_dot_config and idx < len(self.user_dot_config[name]):
                    current_tid = self.user_dot_config[name][idx]
                max_target_id = max(max_target_id, current_tid)
                found_dots.append({'name': name, 'time': t, 'idx': idx, 'tid': current_tid});
                counts[name] += 1
        if max_target_id < 2 and any(x[2] > 1 for x in self.loaded): max_target_id = 2
        if not found_dots: messagebox.showinfo("提示", "轴内没有检测到 DoT 技能，无需配置目标。"); return

        win = tk.Toplevel(self.root)
        win.title("多目标与上天配置")
        win.geometry("600x700")
        
        try:
            # 优先尝试 PNG
            png_path = resource_path("SAM.png")
            if os.path.exists(png_path):
                # 注意：必须保持 img 的引用，防止被垃圾回收，虽然在这里它是局部变量
                # 但只要窗口初始化完成即可。为了稳妥，也可以挂在 win 对象上
                win.icon_image = tk.PhotoImage(file=png_path)
                win.iconphoto(False, win.icon_image)
            else:
                # 其次尝试 ICO
                ico_path = resource_path("ffxiv_ndps.ico")
                if os.path.exists(ico_path):
                    win.iconbitmap(ico_path)
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
        d = []
        for l in self.txt_dt.get("1.0", tk.END).split('\n'):
            l = l.replace('(', '').replace(')', '').replace('，', ',').strip()
            if l:
                try:
                    d.append(tuple(map(float, l.split(','))))
                except:
                    pass
        return d

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
        self.btn_run.config(state="disabled", text="计算中...")
        self.progress_var.set(0)
        self.txt_res.delete("1.0", tk.END)
        for i in self.tree_log.get_children(): self.tree_log.delete(i)
        for i in self.tree_stats.get_children(): self.tree_stats.delete(i)
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
            st['str'] = int(st['力量 (STR)']);
            st['crt'] = int(st['暴击 (CRT)'])
            st['det'] = int(st['信念 (DET)']);
            st['dh'] = int(st['直击 (DHT)'])
            st['sks'] = int(st['技速 (SKS)']);
            st['wd'] = int(st['武器性能'])
            st['delay'] = float(st['攻击间隔']);
            st['party_bonus'] = float(st['队伍加成'])
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

            sim = SamuraiSimulator(st, self.loaded,
                                   downtime_config=final_dt_config,
                                   dot_config=self.user_dot_config,
                                   multi_boss_mode=is_multi,
                                   global_downtime_list=final_global_dt_list,
                                   iterations=iters,
                                   custom_snaps=custom_snaps_list)

            dps_l, dur, last_h, stats_pkg, log = sim.run_batch(threshold=target_threshold, progress_callback=self.update_prog)

            m_dps = statistics.mean(dps_l)
            sd_dps = statistics.stdev(dps_l) if iters > 1 else 0
            base_gcd, shifu_gcd = SamuraiSimulator.calculate_gcd(st['sks'])

            ui_data = {
                'm_dps': m_dps, 'sd_dps': sd_dps, 'dur': dur, 'last_h': last_h,
                'stats_pkg': stats_pkg, 'log': log, 'dps_l': dps_l, 'iters': iters,
                'sim_instance': sim, 'gcd_info': (base_gcd, shifu_gcd)
            }
            self.root.after(0, lambda: self.finish_ui(ui_data))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.btn_run.config(state="normal", text="▶ 运行模拟"))

    def finish_ui(self, data):
        m_dps, sd_dps = data['m_dps'], data['sd_dps']
        dur, last_h = data['dur'], data['last_h']
        stats_pkg, log = data['stats_pkg'], data['log']
        dps_l, iters = data['dps_l'], data['iters']
        sim, gcds = data['sim_instance'], data['gcd_info']

        t = self.txt_res
        t.insert(tk.END, "【面板与理论数据】\n", "h2")
        t.insert(tk.END, f"力量: {sim.base_str} | 武器性能: {sim.stats['wd']} | 技速: {sim.stats['sks']}\n")
        t.insert(tk.END, f"暴击: {sim.stats['crt']} -> {sim.crit_rate * 100:.3f}% (x{sim.crit_dmg:.3f})\n")
        t.insert(tk.END, f"直击: {sim.stats['dh']} -> {sim.dh_rate * 100:.3f}%\n")
        t.insert(tk.END, f"信念: {sim.stats['det']} | GCD(风花): {gcds[1]:.3f}s (Base: {gcds[0]:.3f}s)\n")
        t.insert(tk.END, "-" * 50 + "\n\n")
        mode_str = "多Boss模式 (自动计算交集)" if sim.multi_boss_mode else "单模式 (读取文本框)"
        t.insert(tk.END, f"当前模式: {mode_str}\n")
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
            s_data = SKILL_DB.get(k)
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
                s_data = SKILL_DB.get(k)
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
                dt_loss = sim.get_effective_downtime_total(t_point)
                eff_duration = max(1.0, t_point - dt_loss)

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
            ico_path = resource_path("ffxiv_ndps.ico")
            if os.path.exists(ico_path):
                win.iconbitmap(ico_path)
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
                dt_loss = sim_instance.get_effective_downtime_total(t)
                eff_duration = max(1.0, t - dt_loss)
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


if __name__ == "__main__":
    root = tk.Tk();
    root.configure(bg="#2b2b2b");
    app = SamuraiApp(root);
    root.mainloop()
