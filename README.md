# FFXIV Personal nDPS Simulator

这是一个面向个人轴的 FFXIV nDPS 模拟器仓库。当前核心目标是：导入排轴/raid-planner 导出的技能轴，按 7.5 版本技能机制、目标数、上天窗口、DoT/宠物/追击/自动攻击与职业资源状态，模拟该玩家自身输出。

完整手册见 [docs/USER_MANUAL.md](docs/USER_MANUAL.md)，当前证据边界见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## 下载安装

推荐普通使用者从 GitHub Releases 下载现代版：

- 最新 Release：<https://github.com/YuukiErii/FFXIV-nDPS-Simulator/releases/latest>
- 现代版文件名：`ffxiv_personal_ndps_v2.exe`

仓库内也保留两套 Windows 发行面：

```text
releases/windows/ffxiv_personal_ndps.exe
releases/windows/ffxiv_personal_ndps_modern/ffxiv_personal_ndps_v2.exe
```

`ffxiv_personal_ndps_v2.exe` 是单文件 Electron 外壳，已内置前端、Python 后端和运行时文件。正常情况下直接双击即可运行；如果 Windows 安全提示未知发布者，选择允许运行即可。

## 两个版本怎么选

### 现代版：`ffxiv_personal_ndps_v2.exe`

现代版是当前推荐的可视化入口，适合日常查看和对照排轴网站。

特点：

- React/Vite/Electron 桌面 UI，视觉和表格更适合长期使用。
- 内置 Python JSON 后端，计算核心仍然走同一套 `src/ffxiv_ndps_simulator/sim.py`。
- 支持导入技能轴 CSV、目标 TXT/JSON、上天/不可选中 Track TXT。
- 支持模拟后 `[start, end)` 时间窗口复算，不重新抽随机数，只重聚合已完成命中。
- 技能详情里展示技能威力、目标数、Buff、必暴/必直暴、平均伤害等信息。
- 适合检查排轴网站的技能数量、目标数、Buff 吃到情况和分段 nDPS。

使用方式：

1. 双击 `ffxiv_personal_ndps_v2.exe`。
2. 选择职业和 7.5 版本。
3. 填入主属性、暴击、信念、直击、技速/咏速、武器基本性能等配装数据。
4. 选择技能轴 CSV。
5. 如有目标文件，选择对应 TXT/JSON；如有上天窗口，选择 `MarkerTrackIndividual` Track TXT。
6. 点击运行模拟。
7. 在总览、技能详情、战斗日志、DoT、资源警告、时间窗口 nDPS 等面板检查结果。

### 稳定版：`ffxiv_personal_ndps.exe`

稳定版是旧 Tk GUI，适合做回归、自测和保守使用。

特点：

- 单文件 Python GUI，界面朴素但链路短。
- 支持 `--self-test`，可快速验证打包资源、13 职业样本、公式层和历史样本。
- 报告导出稳定，适合留 Markdown/CSV 证据。
- 当现代版 UI 行为异常时，可以用稳定版判断是 UI 问题还是模拟核心问题。

使用方式：

```powershell
.\releases\windows\ffxiv_personal_ndps.exe
```

自测：

```powershell
.\releases\windows\ffxiv_personal_ndps.exe --self-test
```

稳定版输入流程与现代版一致：先选职业和属性，再导入 CSV，按需要补目标文件和上天 Track TXT，最后运行并导出报告。

## 输入文件

最常见输入组合：

- 技能轴 CSV：必须。来自 XIV in the Shell、raid-planner 或兼容导出。
- 目标 TXT/JSON：可选。用于保留多目标、换目标和目标数信息。
- Track TXT：可选。用于解析上天/不可选中窗口，作为全局 downtime。

CSV 至少应包含时间和技能名。若包含 `castTime`、`positionalHit`、target metadata 等字段，模拟会更接近原轴。身位默认视为打中；如果要模拟没打到身位，需要显式给 `positionalHit=false`。

Track TXT 会识别描述里含 `不可选中`、`上天` 或 `untargetable` 的 marker，并按 `time` 到 `time + duration` 转成 downtime。

## 模拟特点和边界

模拟内容包括：

- 玩家自身直伤、DoT、自动攻击。
- 宠物、召唤物、分身、追击、延迟结算。
- 个人 Buff、职业资源、连击、触发状态、读条快照和多目标衰减。
- 战斗目标不可选中时的停手/DoT tick 归属。
- 当前完成运行的时间窗口重聚合。

当前不做的事：

- 不等同 FFLogs 严格 nDPS；外部团队 Buff 收益和队友贡献分配属于未来 Task M。
- 不从日志中反推隐藏 proc；触发类技能如果已经写在轴里，默认该技能已经触发。
- 不自动修正排错的轴；资源警告只提示，不阻止模拟。

因此，结果适合比较个人轴、技能数量、Buff 覆盖、窗口输出和机制建模；如果要作为最终日志级结论，还需要真实 log、AMAS 或外部审计继续确认。

## 当前职业稳定性口径

这里的“稳定”指当前已经逐项检查并在本项目口径下确认无已知模拟机制问题；不是 FFLogs 官方认证。

确认稳定的五个职业：

| 职业 | 当前口径 |
| --- | --- |
| SAM | 已完成机制与样本检查；身位默认命中；默想/剑气/返/奥义等当前无已知问题。 |
| RPR | 已完成机制检查；团契牺牲默认 8 层；夜游魂、虚无/夜游、团辅与收割链路当前无已知问题。 |
| RDM | 已完成机制检查；鼓励只作用自身魔法伤害，不作用物理技能、飞刺/六分/交剑/移转等；读条与双咏/促进已核对。 |
| PCT | 已完成机制检查；星空、画 motif/muse、锤、彗星、多目标衰减、必直暴展示与读条快照已核对。 |
| BLM | 已完成机制检查；7.5 AF/UI 不过期；多目标、双目标 DoT、咏速读条与滑步快照已核对。 |

仍需保持谨慎、继续用真实轴/日志验证的八个职业：

| 职业 | 为什么仍标为谨慎 |
| --- | --- |
| NIN | 7.5 官方机制已核对，NIN 830 轴已校准；仍建议继续用真实 log 验证介毒/百雷/分身/忍气窗口的最终数值边界。 |
| MNK | 官方机制已核对；斗气含队友平均给层，义结金兰上限 10 已建模；随机开斗气与外部轴隐藏信息仍需真实样本确认。 |
| DRG | 官方机制已核对；红龙血/Power Surge 防双算已加测试；仍建议用真实长轴继续验证跳跃追击、红龙窗口和自动攻击边界。 |
| VPR | 官方机制已核对；猎手、迅鳞、毒、祖灵、响尾蛇/双牙链已建模；固定轴不会因迅鳞自动重排 GCD，只影响模拟生成的自动攻击。 |
| BRD | 官方机制已核对；军神 Muse/Ethos 已补；Repertoire/proc 若轴里没有隐藏明细，仍按“轴里出现即已触发”处理。 |
| MCH | 官方机制已核对；野火、过热、回转飞锯/掘地飞轮、皇后、电量缩放已建模；外部导出里 Heat Blast/Queen attribution 仍可能有口径差。 |
| DNC | 官方机制已核对；大舞默认四步吃满，Enhanced Esprit +10 已补；舞伴贡献仍不属于当前个人 nDPS 口径。 |
| SMN | 官方机制已核对；召唤物使用已校准的 0.8 有效宠物系数；仍建议用合法真实轴继续确认召唤循环与宠物时间轴。 |

换句话说：这八个职业不是“已知有错”，而是证据等级低于上面五个，后续如果要宣称完全稳定，需要继续拿真实 logs 或等价外部审计做最终数值确认。

## 开发与打包

源码 GUI：

```powershell
.\.venv\Scripts\python.exe .\src\ffxiv_ndps_simulator\sim.py
```

现代 UI 开发：

```powershell
cd .\apps\ndps-ui
npm install
npm run dev
npm run desktop
```

重新打包：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_ffxiv_ndps_simulator_exe.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build_modern_ndps_ui.ps1
```

常用验证：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\smoke_damage_formula.py
.\.venv\Scripts\python.exe scripts\scan_skill_coverage.py examples\skill_lines --issues-only --show-skills
.\releases\windows\ffxiv_personal_ndps.exe --self-test
```

## 仓库结构

- `src/ffxiv_ndps_simulator/`：模拟核心。
- `apps/ndps-ui/`：现代 React/Electron UI。
- `scripts/`：打包、桥接、校准和扫描脚本。
- `examples/skill_lines/`：样本轴、目标文件、Track 文件。
- `results/calibration/`：校准和对照证据。
- `releases/windows/`：可直接运行的 Windows 发行文件。
- `docs/`：用户手册、项目状态和历史归档。
