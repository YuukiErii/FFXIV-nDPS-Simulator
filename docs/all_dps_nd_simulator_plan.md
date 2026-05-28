# 全职业个人 nDPS 模拟器实现计划

更新时间：2026-05-27

## 1. 目标

把当前从武士模拟器扩展出来的原型，做成一个面向所有 DPS 职业的个人 nDPS 模拟器：

1. 用户在排轴网排好轴并下载 CSV。
2. 模拟器直接导入 CSV，必要时再导入同名 TXT/JSON 目标列表。
3. 用户选择职业、输入面板属性、配置上天/多目标。
4. 程序输出该轴的个人 nDPS/RD 分布、技能明细、阶段 RD、极值样本和导出报告。

本项目的核心不是自动生成最优循环，而是评估“用户已经排好的轴”。因此 CSV 中出现的技能顺序是事实来源；模拟器负责把这些技能在对应时间点解释成正确的 potency、buff、DoT、follow-up、AOE、普攻、目标数和随机暴直结果。

## 2. nDPS 定义

为避免和 FFLogs 语义混淆，先固定本工具内部定义：

- **个人 nDPS / 个人 RD**：只计算玩家本人技能、DoT、普攻、宠物或召唤物等归属于本职业的伤害。
- 默认不引入外部团辅时间轴；因此没有外部团辅收益需要剔除。
- 保留自身 buff、职业特性、药水、宠物/召唤物、自身 debuff、目标数、上天、AOE 衰减。
- DPS 分母默认使用当前脚本逻辑：最后有效出伤时间减去全局上天损失；后续需要在 UI 中明确标注。

后续如果要接近 FFLogs 的严格 nDPS，需要新增外部 buff 输入、剔除外部 buff gain、处理团辅贡献归属。这属于第二阶段产品能力，不放在当前 MVP 的关键路径里。

## 3. 当前状态

已经完成的基础：

- 原武士版 `sim_test.py` 已备份到 `src/ffxiv_ndps_simulator/backups/sim_test_sam_only_20260527.py`。
- `src/ffxiv_ndps_simulator/xiv_job_data.py` 能从 `game.txt` 提取 13 个 DPS 职业资料：
  - 近战：MNK, DRG, NIN, SAM, RPR, VPR
  - 远敏：BRD, MCH, DNC
  - 法系：BLM, SMN, RDM, PCT
- `src/ffxiv_ndps_simulator/xiv_skill_provider.py` 已接入本地 `.venv` 中的 `ama_xiv_combat_sim`，可读取技能基础数据：
  - potency
  - base potency
  - cast
  - application delay
  - combo 前置
  - guaranteed crit/direct hit
  - DoT potency/duration
  - AOE 衰减
  - 部分 offensive buff
- `src/ffxiv_ndps_simulator/xiv_axis_csv.py` 已新增排轴网 CSV 适配层：
  - 支持 `time, action, isGCD, castTime` 表头格式。
  - 兼容旧的前两列格式。
  - 兼容少量一列 TTS skillline CSV。
  - 保留 `raw_name`, `is_gcd`, `cast_time`, `row_no`, `targets` 元信息。
- `src/ffxiv_ndps_simulator/sim.py` 和 `src/ffxiv_ndps_simulator/sim_test.py` 已同步：
  - 职业下拉框。
  - 主属性/速度属性输入。
  - job-aware damage 参数。
  - CSV 实际 `castTime` 优先于技能库默认 cast。
  - CSV/TXT 技能名匹配支持中英文转换。

已验证：

- `examples/skill_lines` 下 80 个 action/axis CSV 全部可解析；另有 8 个 xivintheshell damage export CSV 作为外部明细输入，不参与默认 coverage 扫描。
- 62 个识别为排轴网 CSV，2 个识别为 TTS skillline CSV。
- 26 组同名 CSV/TXT JSON 目标列表都能匹配。
- SAM、NIN、RPR、PCT、BLM 代表轴已能跑出模拟结果。
- 2026-05-27 追加 8 条由 `xivintheshell/xivintheshell` 当前站点导出的职业 smoke CSV，使 MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 也有排轴网格式样本可用于导入与状态机回归。
- 2026-05-27 追加 8 条 xivintheshell 手排长轴、对应 Record JSON、damage export CSV，并生成 `results/calibration/*_xivintheshell_long_skill_comparison.csv` 技能级对照表。

当前主要问题：

- 现在是“全职业可跑原型”，不是“全职业可信模拟器”。
- 非武士职业仍需逐职业数值精校；新增 smoke/手排长轴和 xivintheshell damage baseline 只能证明导入、状态机路径与外部明细可对照，不能替代真实副本日志或 AMAS/FFLogs 级校准。
- 伤害公式仍是从原武士脚本延展出来的简化公式，尚未完整替换为 `damage_cal.txt` / `stat_fns.txt` / `game.txt` / `stores.txt` 中的精确公式。
- UI、类名、报告文案仍有武士历史遗留。

## 4. 总体架构目标

建议最终整理成下面的模块边界：

```text
src/ffxiv_ndps_simulator/
  sim.py                       # GUI 入口，后续改名或保留兼容
  sim_test.py                  # 实验入口，后续可合并或删除
  xiv_axis_csv.py              # 排轴网 CSV/TXT 解析与轴事件标准化
  xiv_job_data.py              # 职业/等级/属性系数
  xiv_skill_provider.py        # 技能库适配层
  xiv_damage_formula.py        # 精确伤害公式
  xiv_sim_core.py              # 通用事件模拟核心
  xiv_report.py                # 报告与导出
  jobs/
    base.py                    # 职业状态机接口
    sam.py
    nin.py
    rpr.py
    pct.py
    ...
  tests/
    test_axis_csv.py
    test_damage_formula.py
    test_job_*.py
```

短期可以先继续在 `sim.py`/`sim_test.py` 内迭代；当机制开始增多时，必须拆出 `xiv_sim_core.py` 和 `jobs/`，否则复杂度会很快压垮单文件脚本。

## 5. 标准数据结构

### 5.1 AxisEvent

所有导入的排轴行应标准化成一个事件结构：

```python
{
    "time": float,
    "name": str,          # 模拟器内部技能名
    "raw_name": str,      # CSV 原始技能名
    "job": str | None,
    "targets": int,
    "target_ids": list[int] | None,
    "is_gcd": bool | None,
    "cast_time": float | None,
    "source": str,
    "row_no": int,
}
```

短期已用 dict 实现；长期可替换为 dataclass。

### 5.2 SkillInfo

技能解析层应输出统一技能信息：

```python
{
    "name": str,
    "potency": int,
    "base_potency": int | None,
    "cast": float,
    "delay": float,
    "combo_prev": list[str],
    "is_aoe": bool,
    "decay": float,
    "dot_potency": int | None,
    "dot_duration": float | None,
    "buff": dict | None,
    "followups": list[dict],
    "guaranteed_crit": bool,
    "guaranteed_dh": bool,
    "damage_class": str,
}
```

`xiv_skill_provider.py` 已经覆盖其中一部分；后续要补齐 follow-up 和 job-specific overrides。

## 6. 阶段路线

### Phase 0：保存基线与输入层稳定化

状态：基本完成。

任务：

- [x] 备份原武士 `sim_test.py`。
- [x] 解析 `examples/skill_lines` 中真实排轴网 CSV 结构。
- [x] 新增 `xiv_axis_csv.py`。
- [x] `sim.py` / `sim_test.py` 使用标准化 axis event。
- [x] CSV 实际 `castTime` 进入模拟。
- [x] CSV/TXT 目标数匹配支持中英文技能名。

剩余小项：

- [x] UI 中增加“导入预览”窗口，显示前 20 行事件。
- [x] UI 中增加“未识别技能列表”。
- [x] UI 中增加“技能覆盖率：识别数 / 总技能数”。
- [x] 导入错误信息改得更人话，例如误选 `_skillline.csv` 时提示“这是 TTS 文件，不是原始排轴 CSV，但已尝试兼容”。

验收标准：

- `examples/skill_lines` 下所有 CSV 解析成功。
- 同名 TXT/JSON 的目标数匹配率接近 100%。
- 导入后用户能立刻看到技能数、格式、目标数来源、未识别技能。

### Phase 1：精确伤害公式模块

目标：把当前简化公式替换成可维护、可测试的公式模块。

任务：

- [x] 新建 `src/ffxiv_ndps_simulator/xiv_damage_formula.py`。
- [x] 从 `stat_fns.txt` 提取并实现：
  - crit rate
  - crit damage multiplier
  - direct hit rate
  - determination multiplier
  - speed multiplier
  - GCD calculation
- [x] 从 `damage_cal.txt` 提取并实现：
  - direct damage
  - DoT damage
  - auto attack
  - guaranteed crit
  - guaranteed direct hit
  - variance 0.95-1.05
  - nested floor 顺序
- [x] 从 `game.txt` / `stores.txt` 对齐：
  - level modifiers
  - job modifiers
  - weapon damage factor
  - trait damage multiplier
  - party bonus
- [x] 支持 deterministic 模式：
  - 固定随机种子。
  - 关闭随机，输出期望伤害。

验收标准：

- 每个基础公式都有 unit test。
- SAM 旧版轴与新公式结果差异可解释。
- 对同一 potency、属性、WD，公式输出能与来源代码或手算结果一致。

### Phase 2：通用模拟核心拆分

目标：把“武士脚本”改造成真正职业无关的事件引擎。

任务：

- [x] 新建 `xiv_sim_core.py`。
- [x] 把 `SamuraiSimulator` 重命名或包装为 `DpsSimulator`。
- [x] 统一事件类型：
  - press
  - damage
  - followup_damage
  - dot_tick
  - auto_attack
  - snapshot
  - history_tick
- [x] 引入第一版 `JobState` 接口：
  - `on_press(name, skill, current_time, snapshot_time)`
  - `consume_combo_override(name, skill, current_time)`
  - `resolve_potency(name, skill, current_time, payload)`
  - `on_damage_resolved(name, skill, current_time, is_combo, payload)`
  - `active_damage_buffs(time)`
  - `auto_attack_interval_multiplier(time)`
  - `format_buffs(active_buffs, has_potion)`
- [x] 保留多目标/上天/DoT 目标归属能力。
- [x] 把 SAM 专属逻辑迁移到 `jobs/sam.py`：
  - 风月
  - 风花
  - 明镜
  - 燕飞强化
  - combo potency
  - 居合/返继续由技能库解析，后续做单项核对

验收标准：

- SAM 输出与拆分前基本一致。
- `DpsSimulator` 不再直接写死“武士”状态名。
- 新职业只需要实现 `JobState`，不需要改核心事件循环。

### Phase 3：技能覆盖报告

目标：任何 CSV 导入后，先判断这条轴能不能被可信模拟。

任务：

- [x] 每次导入后生成 coverage report。
- [x] 分类展示：
  - 已识别且有伤害。
  - 已识别但 0 伤害 buff/移动/减伤技能。
  - 未识别技能。
  - 识别但需要职业状态机支持的技能。
  - follow-up 未建模技能。
  - 目标数缺失或来源为默认 1 的技能。
- [x] 在报告中显示：
  - 总技能行数。
  - 有效伤害技能数。
  - 0 伤害技能数。
  - 未识别技能数。
  - DoT 数。
  - AOE 技能数。
  - 多目标技能数。

验收标准：

- 用户导入 CSV 后，不跑模拟也知道这条轴当前可信度。
- 未识别技能为 0 才允许标记为“可模拟”。
- 如果职业状态机未完成，报告明确标记“结果仅供趋势参考”。

### Phase 4：职业状态机分批实现

原则：

- 每个职业先支持“排轴 CSV 中出现的技能解释正确”，不要求自动判断轴是否合法。
- 资源检查先做警告，不阻止模拟。
- 每个职业都要有至少一条 xivintheshell 导出的 CSV 作为 smoke test；真实副本长轴另作为数值精校门槛。

#### 4.1 SAM：武士

当前最接近完成。

任务：

- [x] 从旧逻辑迁移到 `jobs/sam.py`。
- [x] 确认 7.2 技能 potency 与当前技能库一致。
- [x] 确认风月、风花、明镜、强化燕飞、返、天道、照破、残心。
- [x] 确认彼岸花 DoT snapshot。
- [x] 确认 AOE 衰减。

验收：

- `examples/skill_lines/sam_m9_m12s` 内典型轴全部能跑。
- 未识别技能为 0。
- 与旧版武士脚本差异有说明。

#### 4.2 RPR：钐镰客

任务：

- [x] 死亡烙印 / 死亡祭品 debuff。
- [x] 灵魂切割、绞决、缢杀、束缚挥割等 combo/positional potency。
- [x] 祭牲、夜游魂、夜游魂衣状态。
- [x] 团契、神秘环、夜游魂派生。
- [x] Communio、Perfectio。
- [x] 宠物/化身 follow-up 归属。

验收：

- `examples/skill_lines/rpr_enuo/reaper.csv` 能无未识别技能运行。
- 技能次数与 CSV 一致。

#### 4.3 NIN：忍者

任务：

- [x] 天/地/人印状态。
- [x] 忍术技能解析：
  - 风魔手里剑
  - 火遁
  - 雷遁
  - 冰晶乱流
  - 劫火灭却
  - 土遁
  - 水遁
- [x] 天地人期间忍术替换。
- [x] 分身、残影镰鼬。
- [x] 雷兽、双牙旋、双牙乱击。
- [x] 攻其不备/毒盛。
- [x] 梦幻三段、六道轮回。
- [x] DoT/地面效果 tick 归属。

验收：

- `examples/skill_lines/nin_m12s_p2/nin_830.csv` 能无未识别技能运行。
- 忍术实际出伤技能不是单纯把 Ten/Chi/Jin 当伤害。

#### 4.4 VPR：蝰蛇剑士

任务：

- [x] 双刃/蛇尾 combo 分支。
- [x] 祖灵降临/觉醒状态。
- [x] 各类替换技能与 follow-up。
- [x] 双目标/AOE 衰减。

验收：

- [x] 已新增 `examples/skill_lines/vpr_xivintheshell_smoke/vpr_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。

#### 4.5 DRG：龙骑士

任务：

- [x] 两套 GCD combo。
- [x] 龙眼/红莲龙血/死者之岸窗口。
- [x] 跳跃类 delay/follow-up。
- [x] 幻象冲、天龙点睛、星龙交错。
- [x] 战斗连祷暴击 buff。

验收：

- [x] 已新增 `examples/skill_lines/drg_xivintheshell_smoke/drg_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。

#### 4.6 MNK：武僧

任务：

- [x] 身形状态。
- [x] 双掌打/破碎拳 buff/debuff。
- [x] 必杀技和脉轮。
- [x] 震脚期间特殊逻辑。
- [x] 义结金兰、疾风迅雷相关倍率。

验收：

- [x] 已新增 `examples/skill_lines/mnk_xivintheshell_smoke/mnk_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。

#### 4.7 MCH：机工士

任务：

- [x] 热量、过热、热冲击。
- [x] 整备 guaranteed crit/dh。
- [x] 野火累计 hit 与结算。
- [x] 自动弩/散射等 AOE。
- [x] Queen 召唤、Queen 技能、延迟伤害归属。
- [x] Drill/Air Anchor/Chain Saw/Excavator。

验收：

- [x] 已新增 `examples/skill_lines/mch_xivintheshell_smoke/mch_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。
- [x] 野火结算必须单独在战斗日志中显示。

#### 4.8 BRD：吟游诗人

任务：

- [x] 两个 DoT 及 Iron Jaws 刷新 snapshot。
- [x] 三首歌状态。
- [x] Repertoire proc 对技能轴中实际技能的影响。
- [x] 直线射击预备、爆发射击替换。
- [x] 光明神的最终乐章、战斗之声、失血箭/九天连箭。

验收：

- [x] 已新增 `examples/skill_lines/brd_xivintheshell_smoke/brd_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。

#### 4.9 DNC：舞者

任务：

- [x] 标准舞/技巧舞步骤与 Finish potency。
- [x] 舞伴相关个人 nDPS 定义。
- [x] Flourish proc。
- [x] Fan Dance proc。
- [x] Saber Dance、Last Dance、Tillana、Finishing Move。
- [x] Devilment、Technical Finish、Standard Finish buff。

验收：

- [x] 已新增 `examples/skill_lines/dnc_xivintheshell_smoke/dnc_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。
- [x] 先只算舞者本人伤害；舞伴收益另列为未来功能。

#### 4.10 BLM：黑魔法师

任务：

- [x] 星极火/灵极冰/灵极心。
- [x] 悖论、绝望、核爆、异言。
- [x] 雷 DoT 与 Thunderhead。
- [x] 黑魔纹、三连咏唱、即刻状态对 castTime 的影响。
- [x] Ley Lines 不应重复影响已由 CSV castTime 表示的读条；当前只记录状态/标签，不重复套速度。
- [x] AOE 法术。

验收：

- [x] 现有 BLM CSV 能无未识别技能运行。
- [x] `castTime` 来源以 CSV 为准，避免重复套用咏速/黑魔纹导致读条偏差。

#### 4.11 SMN：召唤师

任务：

- [x] 龙神/不死鸟/三宝石召唤状态。
- [x] 宝石技能替换。
- [x] 能量抽取、溃烂爆发、痛苦核爆。
- [x] Deathflare、Akh Morn、Rekindle、Enkindle 等 follow-up。
- [x] 宠物/召唤物伤害归属。

验收：

- [x] 已新增 `examples/skill_lines/smn_xivintheshell_smoke/smn_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。

#### 4.12 RDM：赤魔法师

任务：

- [x] 黑白魔元状态。
- [x] 连续咏唱对 castTime 的处理。
- [x] 近战 combo 替换。
- [x] 魔元化、倍增。
- [x] Scorch、Resolution、Vice of Thorns、Prefulgence。
- [x] Embolden 自身 buff。

验收：

- [x] 已新增 `examples/skill_lines/rdm_xivintheshell_smoke/rdm_xivintheshell_smoke.csv`，由 xivintheshell 站点导出，用于导入/状态机 smoke；仍需真实副本长轴做数值精校。

#### 4.13 PCT：绘灵法师

任务：

- [x] Creature/Weapon/Landscape motif 状态。
- [x] Muse 技能和 follow-up。
- [x] Hammer combo。
- [x] Subtractive Palette、Hyperphantasia、Rainbow Drip。
- [x] Starry Muse、Star Prism。
- [x] Mog/Madeen 等延迟伤害。
- [x] 长读条技能使用 CSV castTime。

验收：

- `examples/skill_lines/pct_fru/23_desaturation.csv` 能无未识别技能运行。
- 重要 follow-up 不漏算。

## 7. 验证数据集

现有可用样本：

```text
examples/skill_lines/sam_m9_m12s/
examples/skill_lines/nin_m12s_p2/nin_830.csv
examples/skill_lines/rpr_enuo/reaper.csv
examples/skill_lines/pct_fru/23_desaturation.csv
examples/skill_lines/mnk_xivintheshell_smoke/mnk_xivintheshell_smoke.csv
examples/skill_lines/drg_xivintheshell_smoke/drg_xivintheshell_smoke.csv
examples/skill_lines/vpr_xivintheshell_smoke/vpr_xivintheshell_smoke.csv
examples/skill_lines/brd_xivintheshell_smoke/brd_xivintheshell_smoke.csv
examples/skill_lines/mch_xivintheshell_smoke/mch_xivintheshell_smoke.csv
examples/skill_lines/dnc_xivintheshell_smoke/dnc_xivintheshell_smoke.csv
examples/skill_lines/smn_xivintheshell_smoke/smn_xivintheshell_smoke.csv
examples/skill_lines/rdm_xivintheshell_smoke/rdm_xivintheshell_smoke.csv
```

仍需补充的数值校准样本：

```text
MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 的真实副本长轴与日志/AMAS 对照
```

每个职业至少准备：

- 1 条 2 分钟木桩轴。
- 1 条真实副本轴。
- 如果职业有明显 AOE/多目标逻辑，再准备 1 条多目标轴。

## 8. 测试计划

### 8.1 CSV 解析测试

- [ ] `time/action/isGCD/castTime` 标准 CSV。
- [ ] UTF-8 BOM。
- [ ] 中文技能名。
- [ ] 英文技能名。
- [ ] 科学计数法时间，例如 `3.55E-15`。
- [ ] 一列 TTS skillline CSV。
- [ ] 空行和异常行。

### 8.2 技能覆盖测试

- [ ] 每个职业导入样本后未识别技能为 0。
- [ ] 0 伤害技能不进入伤害统计，但保留在日志中。
- [ ] DoT 技能识别并产生 tick。
- [ ] AOE 技能目标数和衰减正确。

### 8.3 公式测试

- [ ] 单一 potency 无 buff。
- [ ] direct hit。
- [ ] crit。
- [ ] crit + direct hit。
- [ ] guaranteed crit/dh。
- [ ] DoT。
- [ ] auto attack。
- [ ] 药水。
- [ ] party bonus。

### 8.4 模拟测试

- [ ] 固定随机种子可复现。
- [ ] deterministic 期望模式可复现。
- [ ] 1 次模拟战斗日志完整。
- [ ] 1000 次模拟平均值和标准差合理。
- [ ] 上天窗口内 press/snapshot/damage/tick 行为符合预期。
- [ ] 多目标 targetList 生效。

## 9. UI 与报告计划

### 9.1 导入页

- [x] 选择职业。
- [x] 选择 CSV。
- [x] 可选选择 TXT/JSON 目标列表。
- [x] 自动显示：
  - CSV 格式。
  - 技能行数。
  - castTime/isGCD 是否存在。
  - TXT 是否匹配。
  - 目标数来源。

### 9.2 覆盖报告页

- [x] 未识别技能表。
- [x] 0 伤害技能表。
- [x] 需要职业机制支持的技能表。
- [x] DoT/AOE/follow-up 技能表。
- [x] 可信度状态：
  - `可模拟`
  - `可跑但结果仅供趋势参考`
  - `不可模拟，存在未识别关键技能`

### 9.3 模拟报告页

保留并整理当前页：

- [x] 总览。
- [x] 战斗日志。
- [x] 技能平均。
- [x] Max DPS 样本。
- [x] 阶段 RD。
- [x] DPS 分布图。
- [x] DPS 分布表。

新增：

- [x] 导出 Markdown 报告。
- [x] 导出 CSV 明细。
- [x] 记录随机种子和版本号。
- [x] 报告顶部显示 nDPS 定义。

## 10. 打包计划

任务：

- [x] 确定唯一入口：`sim.py` 或新建 `xiv_nd_simulator.py`。
- [x] 清理武士命名：
  - `SamuraiSimulator` -> `DpsSimulator`
  - `SamuraiApp` -> `DpsSimulatorApp`
  - 窗口标题改为 `FFXIV Personal nDPS Simulator`
- [x] PyInstaller 打包脚本。
- [x] 把 `game.txt`、`stat_fns.txt`、`damage_cal.txt` 或生成后的 Python 模块纳入资源。
- [x] 确保 `ama_xiv_combat_sim` 依赖可被打包或可替换为本地静态技能数据。
- [x] 加 `--self-test` 命令，打包后可快速验证。

验收标准：

- 双击 EXE 可运行。
- 源码和 EXE 的 `--self-test` 都通过。
- 导入 13 个 DPS 职业 smoke CSV 和至少 4 个历史真实样本可跑。
- 资源路径在 PyInstaller 环境下正常。

## 11. 优先级建议

当前推荐顺序（2026-05-27，Task A-G 已完成，Task H 已有 xivintheshell damage baseline 后）：

1. 固化回归基线：保留 80 个 action/axis CSV 全量扫描、8 个 xivintheshell smoke CSV 单元测试、8 个 long-axis damage comparison、公式 smoke，作为每次改动后的最小必跑门槛。
2. 逐职业数值精校：从 `results/calibration/*_xivintheshell_long_skill_comparison.csv` 开始，按技能明细对齐 potency、combo、替换技能、DoT snapshot、pet/Queen/summon follow-up、舞步/野火/召唤等特殊结算。
3. 真实副本/日志补强：在可获得时用 AMAS 输出、FFLogs 可核对日志或真实副本长轴替换/补强手排 xivintheshell 样本。
4. 增加资源合法性校验：先做 warning-only，不阻断模拟；在覆盖报告和模拟报告里显示魔元、查克拉、舞步、召唤状态、祖灵层数等是否合法。
5. 清理 UI 与报告：去掉武士历史命名，明确个人 nDPS/RD 定义，补 Markdown/CSV 导出和技能数据版本标注。
6. 产品化打包：唯一入口、`--self-test`、PyInstaller 脚本、资源/依赖路径验证、EXE smoke。
7. 第二阶段再做高级 nDPS：外部团辅剔除、舞伴/队友收益、队伍 nDPS 分摊。

理由：

- 覆盖报告会立刻告诉我们“哪里还不可信”。
- 精确公式越早抽出，后续职业不会在错误公式上反复调。
- 先用 SAM 建立 `JobState` 模板，可以降低后续职业接入成本。
- 现在所有 DPS 职业都有导入 smoke，后续瓶颈已经从“能不能跑”转为“是否能被真实副本/日志证据校准”。

## 12. 当前下一步可执行任务

最建议马上做的任务：

### Task A：新增技能覆盖报告

状态：已完成（2026-05-27）。

交付：

- [x] `SkillResolver` 提供 `classify_skill(name, job)`。
- [x] 导入 CSV 后生成 coverage 数据。
- [x] GUI 新增一个“导入覆盖”页。
- [x] 报告未识别技能、0 伤害技能、DoT/AOE 技能、需要状态机技能。

验收：

- [x] 对 `examples/skill_lines` 全部 CSV 扫描，输出每个文件的未识别技能数。
- [x] SAM/NIN/RPR/PCT 样本能列出清晰覆盖信息。

实现记录：

- `src/ffxiv_ndps_simulator/sim.py` 和 `src/ffxiv_ndps_simulator/sim_test.py` 新增覆盖分类、导入覆盖页、目标数来源标记。
- `scripts/scan_skill_coverage.py` 可扫描单个 CSV、目录或整个 `examples/skill_lines`。
- 2026-05-27 验证：当时 `examples/skill_lines` 下 64 个 CSV 均可扫描，未识别技能事件为 0；NIN/RPR/PCT/BLM 已完成样本级状态机后，全量扫描 unknown / needs_state / followup 均为 0。

### Task B：建立精确公式测试骨架

状态：已完成（2026-05-27）。

交付：

- [x] `xiv_damage_formula.py`
- [x] `tests/test_damage_formula.py`
- [x] 若暂时没有 pytest，也可以先做 `scripts/smoke_damage_formula.py`。

验收：

- [x] 用固定属性、固定 potency 输出 direct / dot / auto 三类伤害。
- [x] 与 `damage_cal.txt` 来源公式逐项对齐。

实现记录：

- `src/ffxiv_ndps_simulator/xiv_damage_formula.py` 新增 `XivDamageFormula`、`FormulaStats`、`DamageModifiers` 和 `DamageBreakdown`。
- 已实现基础 stat 函数、direct damage、physical/magical DoT、auto attack、guaranteed crit/direct hit bonus、0.95-1.05 方差、trait/single/damage buff 结算和 deterministic 期望值。
- `scripts/smoke_damage_formula.py` 固定 SAM 属性验证：`direct_base_420=33823`，`dot_base_50=4073`，`auto_base_90=6448`，`direct_expected=42451.915271`。
- 2026-05-27 验证：`py_compile` 通过；smoke 通过；基础 stat 函数与 venv 中 `ama_xiv_combat_sim.simulator.calcs.stat_fns.StatFns` 交叉检查通过。

### Task C：SAM JobState 迁移

状态：已完成（2026-05-27）。

交付：

- [x] `jobs/base.py`
- [x] `jobs/sam.py`
- [x] `DpsSimulator` 使用 `JobState`。

验收：

- [x] SAM 典型轴输出与当前版本一致。

实现记录：

- 新增 `src/ffxiv_ndps_simulator/jobs/base.py`、`src/ffxiv_ndps_simulator/jobs/sam.py` 和 `src/ffxiv_ndps_simulator/jobs/__init__.py`。
- `src/ffxiv_ndps_simulator/sim.py` / `src/ffxiv_ndps_simulator/sim_test.py` 已把核心模拟类包装为 `DpsSimulator`，并保留 `SamuraiSimulator = DpsSimulator` 兼容旧 UI 调用。
- SAM 的风月、风花、明镜、强化燕飞、combo potency、伤害 buff 标签和普攻间隔已从核心事件循环迁移到 `SamJobState`。
- 2026-05-27 验证：`py_compile` 通过；固定随机种子 `20260527` 回放 `examples/skill_lines/sam_m9_m12s/m10s_217.csv`，与迁移前基线一致：`hits=726`，`last_hit=533.795`，`skills=27`，`targets=27`，`total_damage=19574726.009502`。

### Task D：Phase 0-3 收尾与通用核心显式化

状态：已完成（2026-05-27）。

交付：

- [x] 新增 `src/ffxiv_ndps_simulator/xiv_sim_core.py`，集中定义 `press/damage/followup_damage/dot_tick/auto_attack/snapshot/history_tick` 事件类型。
- [x] `DpsSimulator` 使用统一事件类型和时间窗工具，保留多目标、上天、DoT 目标归属能力。
- [x] GUI 新增“导入预览”页，显示标准化后的前 20 行事件、CSV 行号、castTime/isGCD、目标数来源。
- [x] `_skillline.csv` 等误选场景的错误提示改为人话说明。
- [x] 新增 `tests/test_damage_formula.py`，覆盖 stat 函数、direct/DoT/auto 三类基础伤害和 deterministic 期望值。

验证：

- [x] `py_compile` 通过。
- [x] `python -m unittest tests/test_damage_formula.py` 通过。
- [x] `scripts/smoke_damage_formula.py` 通过。

### Task E：RPR / NIN / PCT 已有真实样本职业状态机第一批

状态：已完成样本级实现（2026-05-27）。

交付：

- [x] 新增 `jobs/rpr.py`：通用 combo、死亡烙印目标 debuff、RPR 样本中 Arcane Circle / Enshroud / Gluttony / Communio / Perfectio 等状态覆盖标记。
- [x] 新增 `jobs/nin.py`：通用 combo、mudra 零伤害解释、Kassatsu 忍术倍率、Bunshin 附加威力、毒盛/百雷铳/攻其不备目标 debuff、Meisui 加成、Phantom Kamaitachi pet 标量。
- [x] 新增 `jobs/pct.py`：Starry Muse 自身增伤，PCT 样本中的 motif / muse / hammer / subtractive / portrait follow-up 覆盖标记。
- [x] `jobs/__init__.py` 增加已建模技能清单，使 coverage report 能区分“已经由状态机解释”和“仍需状态机”。

验证：

- [x] `examples/skill_lines/rpr_enuo/reaper.csv` 强制 RPR 扫描无 unknown / needs_state / followup 问题，并可运行模拟。
- [x] `examples/skill_lines/nin_m12s_p2/nin_830.csv` 强制 NIN 扫描无 unknown / needs_state / followup 问题，并可运行模拟。
- [x] `examples/skill_lines/pct_fru` 强制 PCT 扫描无 unknown / needs_state / followup 问题，`23_desaturation.csv` 可运行模拟。

边界：

- 当前是“已有样本轴可信可跑”的第一批实现；资源合法性仍按计划只做宽松解释，不阻断模拟。
- 多目标 debuff 已按目标 ID 留接口；AOE 下逐目标 debuff 精细拆分后续还可以继续收紧。

### Task F：BLM 真实样本职业状态机第二批

状态：已完成样本级实现（2026-05-27）。

交付：

- [x] 新增 `jobs/blm.py`：星极火/灵极冰、灵极心、天语、悖论、星极魂、Polyglot、Thunderhead、黑魔纹、即刻/三连状态。
- [x] BLM 火/冰属性威力倍率与天语 1.27 增伤接入 `JobState`，雷 DoT 快照沿用当前通用 DoT 机制。
- [x] `SkillResolver` 为 provider 技能附带 `amas_name`，职业状态机可稳定处理英文别名和中文技能名。
- [x] 通用零伤害技能（如 `Tincture` / `Surecast` / `Lucid Dreaming`）补齐可运行技能对象，避免 coverage 能解释但模拟阶段被跳过。
- [x] Ley Lines / Swiftcast / Triplecast 只做状态解释，不重复修改已由 CSV 给出的 `castTime`。
- [x] 新增 `tests/test_blm_state.py`，覆盖星极火倍率、星灵移位切换和样本 BLM 技能分类放行。

验证：

- [x] `py_compile` 通过。
- [x] `python -m unittest tests/test_damage_formula.py tests/test_blm_state.py` 通过。
- [x] `scripts/smoke_damage_formula.py` 通过。
- [x] `scripts/scan_skill_coverage.py examples/skill_lines --issues-only` 无输出；当时 64 个 CSV 全部为可模拟，unknown / needs_state / followup 均为 0。
- [x] `m10s_1b3.csv`、`m10s_905_plus_1foul.csv`、`m10s_3b3*_7456f4.csv` 三个 BLM 代表轴可完成一次模拟。

边界：

- 当前仍是样本级宽松状态机：资源合法性用于解释和倍率，不阻断非法轴。
- 黑魔纹、即刻、三连不再额外调整读条；读条时间继续以 CSV `castTime` 为准。

### Task G：全 DPS 职业状态机补齐与整体回归

状态：代码已完成，缺样本职业已补入排轴网导出 smoke CSV；真实副本长轴仍保留为数值精校边界（2026-05-27）。

交付：

- [x] 新增 `jobs/mnk.py`：身形、震脚、红莲/义结/疾风窗口、必杀技宽松解释。
- [x] 新增 `jobs/drg.py`：龙剑单 hit 强制暴击、猛枪、战斗连祷、红龙窗口与跳跃/龙血技能覆盖。
- [x] 新增 `jobs/vpr.py`：猎手/迅鳞、祖灵降临、Generation/Legacy 与双刃分支覆盖。
- [x] 新增 `jobs/brd.py`：两 DoT、三首歌、猛者、战斗之声、光明神最终乐章覆盖。
- [x] 新增 `jobs/mch.py`：整备强制 CDH、过热、野火 6 hit 结算、Queen 宽松归属。
- [x] 新增 `jobs/dnc.py`：标准舞/技巧舞、Devilment、Finishing Move/Tillana、舞步状态覆盖。
- [x] 新增 `jobs/smn.py`：三 Demi、三宝石、Searing Light、Aetherflow 与召唤物技能覆盖。
- [x] 新增 `jobs/rdm.py`：黑白魔元、连续咏唱、魔元化/鼓励、近战 combo 与终结链覆盖。
- [x] 新增 `tests/test_all_job_states.py`，覆盖 13 个 DPS 职业的状态机创建、关键技能识别、合成 smoke、MCH 野火与单 hit 强制暴击。

验证：

- [x] `python -m unittest discover -s tests` 通过（13 tests）。
- [x] `py_compile` 通过。
- [x] `scripts/scan_skill_coverage.py examples/skill_lines --issues-only --show-skills` 无问题输出。
- [x] 追加 smoke 轴前，`examples/skill_lines` 下原有 64 个 CSV 均可完成一次模拟，simulation failures 为 0。
- [x] 新增 8 条 xivintheshell 站点导出 smoke CSV 后，`examples/skill_lines` 下 72 个 CSV 扫描无 unknown / needs_state / followup 问题。
- [x] 新增的 MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM smoke CSV 均可完成一次模拟且总伤害为正。
- [x] 13 个 DPS 职业合成 smoke 均可完成一次模拟且总伤害为正。
- [x] `src/ffxiv_ndps_simulator/sim.py` 与 `src/ffxiv_ndps_simulator/sim_test.py` 已同步。

边界：

- MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 目前已有 xivintheshell 导出 smoke CSV；这些样本覆盖导入格式和状态机路径，但还不是完整真实副本长轴，真实副本轴补入后仍需做逐职业数值校准。
- 资源合法性仍按本计划原则做宽松解释，不阻断模拟。
- 舞伴收益、队友 nDPS 分摊、召唤物/Queen 的逐 tick 精确时间轴仍可作为后续精校项目。

### Task H：真实副本长轴与外部对照

状态：xivintheshell 长轴与 damage-export 技能级 baseline 已完成；真实日志/AMAS 数值对照仍待补齐。

目标：

- 把当前“xivintheshell smoke 轴可跑”推进到“长轴可回放，并最终能用真实副本/外部明细核对”。
- 为每个缺长轴职业至少准备 1 条真实副本排轴 CSV，并保留同名 JSON/TXT 目标列表或来源说明。
- 优先覆盖 MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM；之后再统一整理 SAM/NIN/RPR/PCT/BLM 的代表轴。

任务：

- [x] 建立 `docs/simulator_calibration_matrix.md`，列出每个职业的样本路径、来源、是否有目标列表、是否有 AMAS/FFLogs/xivintheshell 伤害明细对照、当前可信等级。
- [x] 为 MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 制作手排 xivintheshell 长轴候选，不再只依赖 20-40 技能的 smoke opener。
- [x] 对新增长轴导出 xivintheshell `time/action/isGCD/castTime` CSV，并保存对应战斗 Record JSON，保证以后可重新导出。
- [x] 用更完整的 xivintheshell damage export 补强手排长轴候选，避免只停留在 action-log 级回归。
- [x] 生成按技能聚合的对照表：次数、目标数、potency、DoT tick / pet / follow-up 等 damage-only 行、总 potency 或单次模拟伤害。
- [ ] 用真实副本日志、AMAS 输出或 FFLogs 可核对日志继续替换/补强手排长轴候选，避免把回归样本误当作实战数值验证。
- [x] 在计划文档或校准矩阵中区分三类状态：`import_smoke_passed`、`mechanic_calibrated`、`log_validated`。

验收：

- 每个 DPS 职业至少有 1 条可回放、可重新导出的样本记录。
- 8 个新增职业不只停留在短 smoke 轴，至少各有 1 条可回放长轴进入扫描和模拟；真实副本/外部对照状态另行标记。
- MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 均有对应 `*_xivintheshell_damage.csv` 和 `results/calibration/*_xivintheshell_long_skill_comparison.csv`。
- 每个职业都有明确的“已校准/未校准”边界说明，不能因为可跑就宣称数值已验证。

### Task I：逐职业数值精校

状态：当前计划内收口完成；统一对照脚本、逐职业审计、归因修复、warning 明细与差异边界记录已建立。

任务：

- [x] 统一技能明细对照脚本，读取模拟器输出和外部对照，按技能名聚合比较：`scripts/compare_xivintheshell_damage.py`。
- [x] 审计 MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 的 comparison CSV，逐项解释 matched、damage-only、axis-no-damage 与 simulator-only 行：`docs/task_i_xivintheshell_comparison_audit.md`。
- [x] 按审计顺序修补 P1/P2 缺口：SMN pet/demi/gem follow-up 归因、MCH Automaton Queen/Heat Blast/Detonator、BRD/DRG/SMN source-aware DoT、RDM caster auto-attack。
- [x] 校准 combo / 替换技能 / buff window：MNK 身形与震脚、DRG 跳跃与红龙、VPR Generation/Legacy、RDM 近战终结链等；当前 xivintheshell baseline 的剩余 count-delta 已标为复核边界。
- [x] 校准 DoT snapshot 与 tick：SAM 彼岸花、BRD 双 DoT + Iron Jaws、BLM 雷、DRG 樱花、SMN/PCT 持续效果；source-aware tick 归因已进入对照表。
- [x] 校准 pet / follow-up：MCH Queen、SMN Demi/宝石召唤、PCT portrait/muse、DNC 舞步/舞伴边界；当前缺少外部 damage key 的行按 xivintheshell gap / evidence boundary 记录。
- [x] 对每个职业留下“差异可解释”记录：哪些差异来自随机数、目标数、上天、个人 nDPS 定义，哪些是实现缺口。

验收：

- 每个职业至少有一张技能级对照表。
- 关键技能的次数和目标数先对齐；potency/伤害差异再逐项收敛。
- 不能通过强行改 CSV 或忽略技能来制造通过。

实现记录：

- 2026-05-27 第一轮 Task I 归因修复已完成：
  - MCH `Automaton Queen` 不再作为单个大威力技能直接结算，改为生成 `Armpunch` x5、`Pilebunker`、`Crowned Collider` follow-up；长轴对照中这三类 external damage-only 行已和本地 sim count 对齐。
  - MCH `Detonator` 在 xivintheshell 对照口径下保留为 0 伤害控制行，`Wildfire` 伤害归回 `Wildfire` 延迟结算；剩余差异是 xivintheshell 同时记录 application/detonation 两类 Wildfire damage row。
  - BRD / DRG / SMN 的 DoT tick 由通用 `Dot Tick` 聚合改为归回来源技能；对照表中不再出现 source-less `Dot Tick` simulator-only 行。
  - RDM 开启 caster auto-attack 路径，并限制为附魔近战链启动后开始；对照从 external-only P1 降为 auto window 计数 P2。
  - 修复 0 威力但会触发后续伤害的末尾技能可能被 `last_skill_hit_time` 提前截断的问题。
- 2026-05-27 第二轮 Task I / Task J 联动修复已完成：
  - 外部 damage export 中 `potency=0` 的状态/召唤记录不再计入 `xiv_damage_events`，`Wildfire` 已和 xivintheshell 正 potency detonation rows 对齐。
  - BRD DoT 挂载改为 `JobState.dot_applications(...)`，`Caustic Bite` / `Stormbite` / `Iron Jaws` 的 sim count 已和外部 damage event count 对齐；过期后按 `Iron Jaws` 不刷新 DoT，并产生资源 warning。
  - MCH `Heat Blast` 保留为本地实际伤害；当前 xivintheshell damage export 对这 10 次按键没有正 potency damage row，审计中标记为 xivintheshell export gap，而不是强行改模拟器输出。
  - `results/calibration/xivintheshell_long_skill_comparison_summary.md` 现在输出每个 long-axis 的资源 warning 数；SMN 长轴有 13 条召唤/宝石合法性 warning，BRD 有 3 条 Iron Jaws refresh warning。
- 2026-05-27 验证：`python -m unittest discover -s tests` 通过（21 tests）；`py_compile` 通过；`scripts/smoke_damage_formula.py` 通过；`scripts/scan_skill_coverage.py examples/skill_lines --issues-only --show-skills` 无问题输出；`scripts/compare_xivintheshell_damage.py` 和 `scripts/audit_xivintheshell_comparisons.py` 已重新生成 Task I 对照与审计。
- 2026-05-27 第三轮 Task I / Task J 收口已完成：
  - `JobState.warn(...)` 现在携带 CSV `row_no`，UI 报告、批量结果、对照脚本和 audit 文档都能显示 warning 数量与技能行号。
  - `scripts/compare_xivintheshell_damage.py` 为 MNK/DRG/VPR/BRD/MCH/DNC/SMN/RDM 输出 `results/calibration/*_resource_warnings.csv`；`docs/task_i_xivintheshell_comparison_audit.md` 会列出每个职业的 warning 明细。
  - Task I 剩余行统一收口为 evidence boundary：SMN 手排长轴合法性、MCH Heat Blast xivintheshell export gap、auto-attack timing drift、MNK/DNC/DRG/BRD 小型 count-delta 等待更强外部参考复核。
- 后续证据边界：如需从 `mechanic_calibrated` 推进到 `log_validated`，仍需真实副本日志、AMAS 输出或等价外部审计结果；这不再是 Task I/J 当前实现缺口。

### Task J：资源合法性与警告系统

状态：当前计划内收口完成；warning-only 基础设施、13 DPS 职业资源检查、UI/报告行号显示与非法轴回归测试已接入。

任务：

- [x] 在 `JobState` 中增加 warning-only resource ledger，不阻断模拟。
- [x] 覆盖主要资源：武士剑气/闪/禅、忍者忍气/忍术序列、镰刀灵魂/魂衣、武僧脉轮/身形、龙骑红龙/幻象冲、蝰蛇祖灵层数、吟游歌曲/proc、机工热量/电量、舞者舞步/扇舞/伶俐、黑魔 MP/冰火/通晓、召唤宝石/Demi、赤魔黑白魔元、绘灵 motif/muse/hammer。
- [x] 覆盖报告显示资源警告数量和技能行号。
- [x] 模拟报告保留“宽松解释”标签：有资源警告时结果仅供趋势参考。
- [x] 新增少量故意非法轴测试，确认 warning 能被触发且不崩溃。

验收：

- 合法 smoke/样本轴 warning 可解释，非法测试轴能明确指出原因。
- UI/报告中能看到资源合法性状态，而不是只在控制台里出现。

实现记录：

- 2026-05-27 `JobState` 新增 `warn(...)` / `get_resource_warnings()`，并补充事件上下文 `row_no`；`run_one_simulation` 和 `run_batch` 会把首轮资源 warning 传给 UI 与对照脚本。
- 已接入第一批 warning：
  - BRD：`Iron Jaws` 在双 DoT 不全时不刷新 DoT，并记录 `brd_iron_jaws_missing_dot`。
  - MCH：`Hypercharge` 热量不足、`Heat Blast` 非过热、`Automaton Queen` 电量不足、`Detonator` 无 Wildfire。
  - SMN：Demi 行动、宝石行动、宝石覆盖、Aetherflow 空栈。
  - RDM：黑白魔元不足、附魔近战 combo 顺序。
- 第三轮补齐剩余职业 warning：
  - SAM：剑气、闪、禅、回返与残心准备状态。
  - NIN：Mudra 序列、忍术结果与忍气支出。
  - RPR：灵魂、魂衣、Enshroud 层数与 Soulsow/Harvest Moon。
  - MNK：身形、震脚/必杀技、脉轮支出。
  - DRG：红龙窗口与 Firstminds' Focus。
  - VPR：Serpent Offering、Reawaken 层数、Rattling Coil、Twinfang/Twinblood 准备状态。
  - DNC：舞步、Standard/Technical Finish、Fan Dance proc、Esprit。
  - BLM：Astral/Umbral、MP、Thunderhead、Polyglot、Astral Soul。
  - PCT：creature/weapon/landscape motif、muse、hammer stack、Starry Muse。
- `tests/test_all_job_states.py::test_resource_warnings_are_non_blocking` 已覆盖 13 DPS 的故意非法轴，并确认 warning 含 `row_no` 且模拟不崩溃。

### Task K：UI、报告与导出收尾

状态：当前计划内完成；唯一入口、报告头、可信等级、Markdown 导出和 CSV 明细导出已接入。

任务：

- [x] 确定唯一入口：保留 `src/ffxiv_ndps_simulator/sim.py`；`src/ffxiv_ndps_simulator/sim_test.py` 改为兼容启动壳，不再复制 UI 代码。
- [x] 清理武士历史命名：`SamuraiApp` 正式替换为 `DpsSimulatorApp`，窗口标题、AppID、主标题和运行路径使用全职业 nDPS simulator 命名；旧 `SamuraiApp` / `SamuraiSimulator` 仅保留兼容 alias。
- [x] 模拟报告顶部显示个人 nDPS/RD 定义、技能数据来源、游戏版本、样本路径、目标数来源、资源合法性状态。
- [x] 增加 Markdown 报告导出。
- [x] 增加 CSV 明细导出：战斗日志、技能聚合、覆盖报告、资源警告，并额外导出 report metadata。
- [x] 报告中区分 `import smoke passed`、`mechanic calibrated`、`log validated`，避免把 smoke 当数值验证。

验收：

- 用户导入 CSV 后，不看代码也能知道该轴处于哪个可信等级。
- 导出的 Markdown/CSV 可以直接作为后续校准证据或 bug report 附件。

实现记录：

- 2026-05-27 Task K 完成：
  - `src/ffxiv_ndps_simulator/sim.py` 为唯一维护入口；`src/ffxiv_ndps_simulator/sim_test.py` 只负责导入 `DpsSimulatorApp` 并启动，避免 GUI 代码双份分叉。
  - 报告概览顶部新增“报告边界与可信等级”，显示个人 nDPS/RD 定义、技能数据源、版本、随机种子、样本路径、目标数来源、coverage 状态、资源 warning 状态，以及 `import_smoke_passed` / `mechanic_calibrated` / `log_validated` 三层证据状态。
  - GUI 新增“导出 Markdown 报告”和“导出 CSV 明细”按钮；CSV 明细包含 `combat_log`、`skill_aggregate`、`coverage_report`、`resource_warnings`、`report_metadata`。
  - 图标路径优先查找 `FFXIV_SIM.*` / `XIV_SIM.*`，再回退到历史 `SAM.*` 资源。

### Task L：打包、自测与发布包验证

状态：已完成（2026-05-28）。

任务：

- [x] 新增模拟器 `--self-test`：扫描关键样本、跑 13 职业 smoke、跑公式 smoke，失败时返回非零退出码。
- [x] 新增 PyInstaller 打包脚本，和 `XIVShellTTS` 打包脚本分开。
- [x] 处理 `ama_xiv_combat_sim` 依赖：能打进包，或生成静态技能数据 fallback。
- [x] 验证 PyInstaller 资源路径：`game.txt`、`stat_fns.txt`、`damage_cal.txt`、技能映射、图标、样本测试路径。
- [x] 生成 release README，说明输入 CSV、可选 JSON/TXT 目标列表、个人 nDPS 定义、已知边界。

验收：

- 源码 `--self-test` 通过。
- EXE `--self-test` 通过。
- 双击 EXE 可打开 GUI。
- 用至少 13 个职业 smoke CSV 和 4 个历史真实样本做 EXE smoke，不依赖开发环境的 `PYTHONPATH`。

实现记录：

- 2026-05-28 Task L 完成：
  - `src/ffxiv_ndps_simulator/sim.py --self-test` 会检查打包资源、13 个 DPS job profile、公式 smoke、13 职业 CSV smoke，以及 SAM/NIN/RPR/PCT 四条历史 target-data 样本；任一失败返回非零退出码。
  - 新增 `scripts/build_ffxiv_ndps_simulator_exe.ps1`，输出 `releases/windows/ffxiv_personal_ndps.exe`，构建目录与 `XIVShellTTS` 分离。
  - PyInstaller 包内验证通过：`game.txt`、`stat_fns.txt`、`damage_cal.txt`、技能映射、图标、`examples/skill_lines` 样本和 `ama_xiv_combat_sim` 均可在 `_MEIPASS` 环境加载。
  - 新增 `releases/windows/ffxiv_personal_ndps_readme.md`，记录输入 CSV、可选 JSON/TXT 目标列表、个人 nDPS/RD 定义、已知边界和重建命令。
  - 验证：源码 `--self-test` 通过；EXE `--self-test` 通过；启动 EXE 后进程保持运行并可打开 GUI；`python -m unittest discover -s tests` 通过（21 tests）；`scripts/smoke_damage_formula.py` 通过；`scripts/scan_skill_coverage.py examples/skill_lines --issues-only --show-skills` 无问题输出。

### Task M：高级 nDPS 与队友收益（二阶段）

状态：MVP 之后。

任务：

- [ ] 支持外部团辅时间轴输入，并可选择剔除外部 buff gain。
- [ ] 舞者舞伴收益、队友吃到团辅的贡献、队伍 nDPS 分摊作为独立报告页。
- [ ] 明确区分个人 RD、个人 nDPS、FFLogs 近似 nDPS、队伍贡献。

验收：

- 在没有外部队友输入时，默认仍输出当前个人 nDPS/RD，不假装接近 FFLogs 严格 nDPS。
- 有外部输入时，报告清楚列出归属规则和不可验证假设。

## 13. 完成标准

达到下面条件时，可以认为第一版 MVP 目标完成：

- 13 个 DPS 职业都能选择并导入排轴网 CSV。
- 每个职业至少有 1 条 xivintheshell 导出 CSV 样本通过 smoke test。
- 导入后未识别技能为 0，或未识别技能明确是无伤害/无关技能。
- 每个职业关键状态机已实现到“排轴可解释、结果可信等级明确”的程度。
- 伤害公式模块化，并有基础公式测试。
- 报告明确显示 nDPS 定义、属性、职业、版本、技能覆盖率、目标数来源。
- 报告明确区分 smoke、机制校准、日志验证三种可信等级。
- 打包后的 EXE 可在当前 Windows 环境运行。

达到下面条件时，可以认为第一版数值可信度完成：

- 13 个 DPS 职业都有真实副本长轴或等价长轴样本。
- 每个职业至少有技能级外部对照表，并记录差异解释。
- 资源合法性 warning 已接入报告。
- DoT/pet/follow-up/舞步/召唤/Queen 等特殊结算已有针对性校准记录。

## 14. 风险与处理

### 风险 1：技能库数据与当前游戏版本不一致

处理：

- 在报告中显示技能数据版本。
- 保留本地覆盖表，对关键技能手工 patch。
- 后续支持一键扫描技能库 coverage。

### 风险 2：复杂职业机制过多，难以一次写完

处理：

- 每个职业先以真实 CSV 样本为验收范围。
- 只模拟“轴里实际出现的技能”。
- 资源合法性先警告，不阻止跑。

### 风险 3：CSV castTime 与模拟器速度公式重复生效

处理：

- 对排轴网 CSV，读条时间优先信任 `castTime`。
- GCD/速度公式主要用于默认技能数据、DoT/AA/公式，不反向修改 CSV 中已经排好的施法时间。

### 风险 4：个人 nDPS 与 FFLogs nDPS 不完全等价

处理：

- UI 和报告写清楚定义。
- 外部团辅剔除作为未来功能，不混入 MVP。

### 风险 5：TXT/JSON 目标列表缺失

处理：

- 没有 TXT 时默认单目标。
- 覆盖报告标记目标数来源为默认。
- 多目标轴建议导入 TXT 或手动配置。
