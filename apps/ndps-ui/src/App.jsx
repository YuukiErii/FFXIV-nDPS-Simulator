import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Download,
  Eye,
  FileSearch,
  FileText,
  Gauge,
  Play,
  Settings2,
  Sparkles,
  Swords,
  Table2,
  Timer,
  Upload,
  Zap,
} from "lucide-react";
import React, { useMemo, useRef, useState } from "react";

const JOBS = ["SAM", "VPR", "MNK", "DRG", "NIN", "RPR", "BRD", "MCH", "DNC", "BLM", "SMN", "RDM", "PCT"];
const WEAPON_DELAYS = {
  MNK: 2.56, DRG: 2.8, NIN: 2.56, SAM: 2.64, RPR: 3.2, VPR: 2.64,
  BRD: 3.04, MCH: 2.64, DNC: 3.12, BLM: 3.28, SMN: 3.12, RDM: 3.44, PCT: 2.96,
};
const MAIN_STAT_DEFAULTS = { NIN: 6490 };
const DEFAULT_STATS = {
  mainStat: 6498, crt: 3605, det: 2426, dh: 1793, sks: 689,
  wd: 158, delay: 2.64, partyBonus: 1.05, version: 7.5,
  iterations: 1000, threshold: 46000,
};
const DEFAULT_SIM_OPTIONS = {
  globalDowntime: "", customSnaps: "", multiBossMode: false,
  downtimeConfig: "", dotConfig: "",
};
const SAMPLE_ROWS = [
  { time: 0, action: "Gyofu", raw: "Gyofu", source: "sample", rowNo: 1 },
  { time: 2.14, action: "Jinpu", raw: "Jinpu", source: "sample", rowNo: 2 },
  { time: 4.28, action: "Gekko", raw: "Gekko", source: "sample", rowNo: 3 },
];
const TABS = [
  ["coverage", "导入覆盖", FileSearch],
  ["preview", "导入预览", Eye],
  ["overview", "模拟报告 (概览)", FileText],
  ["log", "战斗日志 (表格)", Activity],
  ["skills", "技能详情 (平均)", Zap],
  ["best", "极值详情 (Max DPS)", Sparkles],
  ["intervals", "阶段 RD 分析", Timer],
  ["distribution", "DPS 分布分析", BarChart3],
  ["distributionTable", "DPS分布表格", Table2],
];

function parseCsvLine(line) {
  const cells = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else current += char;
  }
  cells.push(current.trim());
  return cells;
}

function parseAxisCsv(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).map((line) => line.trim())
    .filter(Boolean).filter((line) => !line.toLowerCase().startsWith("sep="));
  if (!lines.length) return [];
  const first = parseCsvLine(lines[0]);
  const headers = first.map((cell) => cell.toLowerCase().replace(/[\s_]/g, ""));
  const hasHeader = headers.includes("time") && (headers.includes("action") || headers.includes("skill"));
  const indexOf = (...names) => names.map((name) => headers.indexOf(name)).find((index) => index >= 0) ?? -1;
  const timeIndex = hasHeader ? indexOf("time") : 0;
  const actionIndex = hasHeader ? indexOf("action", "skill", "name") : 1;
  const castIndex = indexOf("casttime", "cast");
  const gcdIndex = indexOf("isgcd", "gcd");
  const targetIndex = indexOf("targets", "targetcount");
  const sourceIndex = indexOf("source");
  const rows = hasHeader ? lines.slice(1) : lines;
  return rows.map((line, offset) => {
    const cells = parseCsvLine(line);
    const time = Number.parseFloat(cells[timeIndex]);
    const action = cells[actionIndex];
    if (!Number.isFinite(time) || !action) return null;
    const gcdValue = gcdIndex >= 0 ? cells[gcdIndex]?.toLowerCase() : "";
    return {
      time, action, raw: action, rowNo: offset + (hasHeader ? 2 : 1),
      castTime: castIndex >= 0 && cells[castIndex] !== "" ? Number.parseFloat(cells[castIndex]) : null,
      isGcd: gcdValue ? ["1", "true", "yes", "gcd"].includes(gcdValue) : null,
      targets: targetIndex >= 0 ? Number.parseInt(cells[targetIndex], 10) || 1 : 1,
      targetSource: targetIndex >= 0 ? "axis" : "default",
      source: sourceIndex >= 0 ? cells[sourceIndex] || "axis" : hasHeader ? "axis_csv" : "positional_csv",
    };
  }).filter(Boolean).sort((left, right) => left.time - right.time);
}

function formatWindowNumber(value) {
  return Number.parseFloat(value.toFixed(3)).toString();
}

function downtimeTextFromPairs(text) {
  const matches = Array.from(String(text || "").matchAll(/(-?\d+(?:\.\d+)?)\s*(?:-|,|，|~|–|—)\s*(-?\d+(?:\.\d+)?)/g));
  return matches.map((match) => [Number.parseFloat(match[1]), Number.parseFloat(match[2])])
    .filter(([start, end]) => Number.isFinite(start) && Number.isFinite(end) && start < end)
    .map(([start, end]) => `${formatWindowNumber(start)}-${formatWindowNumber(end)}`).join(", ");
}

function markerTrackDowntimeText(text) {
  let data;
  try { data = JSON.parse(String(text || "").replace(/^\uFEFF/, "").trim()); }
  catch { return downtimeTextFromPairs(text); }
  if (!data || (data.fileType !== "MarkerTrackIndividual" && !Array.isArray(data.markers))) return "";
  const markers = Array.isArray(data.markers) ? data.markers : [];
  const descriptions = markers.map((marker) => String(marker?.description || "").toLowerCase()).filter(Boolean);
  const keywords = ["不可选中", "上天", "untargetable"];
  return markers.filter((marker) => !descriptions.length || keywords.some((word) => String(marker?.description || "").toLowerCase().includes(word)))
    .map((marker) => [Number.parseFloat(marker?.time), Number.parseFloat(marker?.duration)])
    .filter(([start, duration]) => Number.isFinite(start) && Number.isFinite(duration) && duration > 0)
    .map(([start, duration]) => `${formatWindowNumber(start)}-${formatWindowNumber(start + duration)}`).join(", ");
}

function fmt(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return value ?? "-";
  return number.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(value, digits = 1) {
  return value === null || value === undefined ? "-" : `${fmt(value, digits)}%`;
}

function seconds(value) {
  return Number.isFinite(Number(value)) ? `${fmt(value, 3)}s` : "-";
}

function formatTime(value) {
  const secondsValue = Number(value) || 0;
  const minutes = Math.floor(secondsValue / 60);
  const rest = secondsValue - minutes * 60;
  return `${minutes}:${rest.toFixed(rest % 1 === 0 ? 0 : 1).padStart(2, "0")}`;
}

function App() {
  const [job, setJob] = useState("SAM");
  const [stats, setStats] = useState(DEFAULT_STATS);
  const [axisFile, setAxisFile] = useState(null);
  const [targetFile, setTargetFile] = useState(null);
  const [trackFile, setTrackFile] = useState(null);
  const [rows, setRows] = useState(SAMPLE_ROWS);
  const [activeTab, setActiveTab] = useState("coverage");
  const [status, setStatus] = useState("sample");
  const [runResult, setRunResult] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState("");
  const [simOptions, setSimOptions] = useState(DEFAULT_SIM_OPTIONS);
  const axisInputRef = useRef(null);
  const targetInputRef = useRef(null);
  const trackInputRef = useRef(null);

  const activeLabel = TABS.find(([key]) => key === activeTab)?.[1] || "";
  const importedSummary = useMemo(() => ({
    duration: rows.length ? Math.max(...rows.map((row) => row.time)) : 0,
    uniqueSkills: new Set(rows.map((row) => row.action)).size,
  }), [rows]);
  const localCoverage = useMemo(() => {
    const grouped = new Map();
    rows.forEach((row) => {
      const item = grouped.get(row.action) || {
        raw_name: row.raw, name: row.action, count: 0, first_time: row.time, last_time: row.time,
        max_targets: row.targets || 1, target_sources_text: row.targetSource || "default",
        tags_text: "-", classification: { category_label: "预览", reason: "运行模拟后显示完整覆盖分类" },
      };
      item.count += 1;
      item.last_time = row.time;
      item.max_targets = Math.max(item.max_targets, row.targets || 1);
      grouped.set(row.action, item);
    });
    return [...grouped.values()];
  }, [rows]);

  async function readAxisFile(file) {
    if (!file) return;
    const text = typeof file.text === "function" ? await file.text() : file.text || "";
    const parsed = parseAxisCsv(text);
    if (!parsed.length) {
      setStatus("error");
      setRunError("无法从该文件解析时间与技能列。");
      return;
    }
    setRows(parsed);
    setAxisFile({ name: file.name, path: file.path || "", text });
    setStatus("ready");
    setRunResult(null);
    setRunError("");
    setActiveTab("preview");
  }

  async function readTargetFile(file) {
    if (!file) return;
    const text = typeof file.text === "function" ? await file.text() : file.text || "";
    setTargetFile({ name: file.name, path: file.path || "", text });
  }

  async function readTrackFile(file) {
    if (!file) return;
    const text = typeof file.text === "function" ? await file.text() : file.text || "";
    setTrackFile({ name: file.name, path: file.path || "", text });
    const downtime = markerTrackDowntimeText(text);
    if (downtime) setSimOptions((current) => ({ ...current, globalDowntime: downtime }));
  }

  const updateStat = (key, value) => setStats((current) => ({ ...current, [key]: Number.parseFloat(value) || 0 }));
  const updateOption = (key, value) => setSimOptions((current) => ({ ...current, [key]: value }));
  const parseNumberList = (value) => String(value || "").replace(/，/g, ",").split(",")
    .map((item) => Number.parseFloat(item.trim())).filter(Number.isFinite);

  async function chooseFile(kind, ref, reader) {
    const method = { axis: "openAxis", target: "openTarget", track: "openTrack" }[kind];
    if (window.ndps?.[method]) {
      const file = await window.ndps[method]();
      if (file) await reader(file);
    } else ref.current?.click();
  }

  async function runSimulation() {
    setRunError("");
    if (!window.ndps?.runSimulation) {
      setRunError("桌面模拟后端未连接。");
      return;
    }
    if (!axisFile?.path) {
      setRunError("请先通过文件选择器导入排轴 CSV。");
      return;
    }
    setIsRunning(true);
    try {
      const result = await window.ndps.runSimulation({
        csv_path: axisFile.path, target_path: targetFile?.path || "", downtime_track_path: trackFile?.path || "",
        job, iterations: Math.max(1, Math.trunc(stats.iterations)), threshold: stats.threshold,
        global_downtime: simOptions.globalDowntime, custom_snaps: parseNumberList(simOptions.customSnaps),
        multi_boss_mode: simOptions.multiBossMode, downtime_config: simOptions.downtimeConfig, dot_config: simOptions.dotConfig,
        stats: {
          main_stat: stats.mainStat, crt: stats.crt, det: stats.det, dh: stats.dh, sks: stats.sks,
          wd: stats.wd, delay: stats.delay, party_bonus: stats.partyBonus, version: String(stats.version),
        },
      });
      setRunResult(result);
      setStatus("simulated");
      setActiveTab("overview");
    } catch (error) {
      setRunError(error?.message || String(error));
      setStatus("error");
    } finally { setIsRunning(false); }
  }

  function exportSnapshot() {
    const payload = { source: axisFile?.name || "sample", target: targetFile?.name || "", track: trackFile?.name || "", job, stats, simOptions, result: runResult };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "ndps-report.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  const summary = runResult?.summary;
  const statusText = { sample: "示例数据", ready: "已导入", simulated: "模拟完成", error: "需要处理" }[status];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <header className="brand-row">
          <div className="brand-mark"><Swords size={21} /></div>
          <div><p>PERSONAL nDPS</p><h1>FFXIV 模拟器</h1></div>
        </header>

        <section className="control-section">
          <SectionTitle icon={<Settings2 size={16} />} title="职业" />
          <div className="job-grid">
            {JOBS.map((item) => (
              <button className={item === job ? "job-button active" : "job-button"} key={item} onClick={() => {
                setJob(item);
                setStats((current) => ({ ...current, delay: WEAPON_DELAYS[item] ?? current.delay, mainStat: MAIN_STAT_DEFAULTS[item] ?? DEFAULT_STATS.mainStat }));
              }} type="button">{item}</button>
            ))}
          </div>
        </section>

        <section className="control-section">
          <SectionTitle icon={<Gauge size={16} />} title="面板属性" />
          <div className="stat-grid">
            {[
              ["mainStat", "主属性"], ["crt", "暴击"], ["det", "信念"], ["dh", "直击"], ["sks", "技速/咏速"],
              ["wd", "武器性能"], ["delay", "武器延迟"], ["partyBonus", "队伍加成"], ["version", "版本"],
              ["iterations", "模拟次数"], ["threshold", "RD 阈值"],
            ].map(([key, label]) => <Field key={key} label={label} value={stats[key]} onChange={(value) => updateStat(key, value)} />)}
          </div>
        </section>

        <section className="control-section">
          <SectionTitle icon={<Timer size={16} />} title="战斗规则" />
          <label className="field wide"><span>全局上天时间</span><input placeholder="60-75, 180-195" value={simOptions.globalDowntime} onChange={(event) => updateOption("globalDowntime", event.target.value)} /></label>
          <label className="field wide"><span>自定义 RD 快照点</span><input placeholder="60, 120.5, 300" value={simOptions.customSnaps} onChange={(event) => updateOption("customSnaps", event.target.value)} /></label>
          <label className="toggle-field"><input checked={simOptions.multiBossMode} onChange={(event) => updateOption("multiBossMode", event.target.checked)} type="checkbox" /><span>多 Boss / 分路 DoT 模式</span></label>
          <label className="field wide"><span>目标上天配置</span><textarea value={simOptions.downtimeConfig} onChange={(event) => updateOption("downtimeConfig", event.target.value)} /></label>
          <label className="field wide"><span>DoT 目标配置</span><textarea value={simOptions.dotConfig} onChange={(event) => updateOption("dotConfig", event.target.value)} /></label>
        </section>

        <div className="sidebar-actions">
          <button className="primary-action" disabled={isRunning} onClick={runSimulation} type="button"><Play size={17} />{isRunning ? "模拟中..." : "运行模拟"}</button>
          <button className="icon-button" disabled={!runResult} onClick={exportSnapshot} title="导出 JSON 报告" type="button"><Download size={18} /></button>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div><p className="page-kicker">{job} / {statusText}</p><h2>{activeLabel}</h2></div>
          <div className="top-metrics">
            <TopMetric label="期望 RD" value={summary ? fmt(summary.expected_dps, 0) : "-"} />
            <TopMetric label="标准差" value={summary ? fmt(summary.std_dps, 0) : "-"} />
            <TopMetric label="Top 1%" value={summary ? fmt(summary.top_1, 0) : "-"} />
            <TopMetric label="时长" value={summary ? seconds(summary.duration) : seconds(importedSummary.duration)} />
          </div>
        </header>

        <section className="file-strip">
          <FileButton file={axisFile} icon={<Upload size={18} />} label="排轴 CSV" onClick={() => chooseFile("axis", axisInputRef, readAxisFile)} onDrop={readAxisFile} />
          <FileButton file={targetFile} icon={<FileText size={18} />} label="目标 TXT" onClick={() => chooseFile("target", targetInputRef, readTargetFile)} onDrop={readTargetFile} />
          <FileButton file={trackFile} icon={<Timer size={18} />} label="不可选中轨道 TXT" onClick={() => chooseFile("track", trackInputRef, readTrackFile)} onDrop={readTrackFile} />
          <div className="import-status"><CheckCircle2 size={18} /><div><strong>{rows.length} 条事件</strong><span>{importedSummary.uniqueSkills} 个技能</span></div></div>
        </section>

        <input accept=".csv,.txt" hidden onChange={(event) => readAxisFile(event.target.files?.[0])} ref={axisInputRef} type="file" />
        <input accept=".txt,.json" hidden onChange={(event) => readTargetFile(event.target.files?.[0])} ref={targetInputRef} type="file" />
        <input accept=".txt,.json" hidden onChange={(event) => readTrackFile(event.target.files?.[0])} ref={trackInputRef} type="file" />

        <nav className="tabbar" aria-label="报告栏目">
          {TABS.map(([key, label, Icon]) => (
            <button className={activeTab === key ? "tab active" : "tab"} key={key} onClick={() => setActiveTab(key)} type="button"><Icon size={15} /><span>{label}</span></button>
          ))}
        </nav>

        {runError && <div className="error-banner"><AlertTriangle size={17} /><span>{runError}</span></div>}
        <section className="panel-surface">
          {activeTab === "coverage" && <CoverageTab result={runResult} rows={runResult?.coverage?.rows || localCoverage} />}
          {activeTab === "preview" && <PreviewTab result={runResult} rows={rows} />}
          {activeTab === "overview" && <OverviewTab result={runResult} />}
          {activeTab === "log" && <CombatLogTab result={runResult} />}
          {activeTab === "skills" && <SkillDetailsTab result={runResult} />}
          {activeTab === "best" && <BestRunTab result={runResult} />}
          {activeTab === "intervals" && <IntervalsTab result={runResult} />}
          {activeTab === "distribution" && <DistributionTab result={runResult} />}
          {activeTab === "distributionTable" && <DistributionTableTab result={runResult} />}
        </section>
      </main>
    </div>
  );
}

function SectionTitle({ icon, title }) { return <div className="section-heading">{icon}<span>{title}</span></div>; }
function Field({ label, value, onChange }) { return <label className="field"><span>{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} /></label>; }
function TopMetric({ label, value }) { return <div className="top-metric"><span>{label}</span><strong>{value}</strong></div>; }

function FileButton({ file, icon, label, onClick, onDrop }) {
  return <button className="file-button" onClick={onClick} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); onDrop(event.dataTransfer.files?.[0]); }} type="button">{icon}<span>{label}</span><strong>{file?.name || "未选择"}</strong></button>;
}

function EmptyState({ needsRun = false }) {
  return <div className="empty-state"><FileSearch size={28} /><strong>{needsRun ? "尚无模拟结果" : "暂无数据"}</strong><span>{needsRun ? "导入排轴并运行模拟后显示。" : "当前栏目没有可显示的记录。"}</span></div>;
}

function ReportTable({ columns, rows, className = "", rowClassName }) {
  if (!rows?.length) return <EmptyState />;
  return <div className="table-scroll"><table className={`report-table ${className}`}><thead><tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr className={rowClassName?.(row) || ""} key={row.key || `${index}-${row.skill || row.name || row.raw_name || "row"}`}>{columns.map((column) => <td key={column.key}>{column.render ? column.render(row) : row[column.key] ?? "-"}</td>)}</tr>)}</tbody></table></div>;
}

function KvGrid({ rows }) {
  return <div className="kv-grid">{rows.map(([label, value]) => <div className="kv-row" key={label}><span>{label}</span><strong>{value === null || value === undefined || value === "" ? "-" : value}</strong></div>)}</div>;
}

function CoverageTab({ result, rows }) {
  const stats = result?.coverage?.stats || {};
  return <div className="view-stack">
    <div className="summary-band">
      <div><span>覆盖状态</span><strong>{result?.coverage?.status || "导入预览"}</strong></div>
      <div><span>总事件</span><strong>{stats.total_events ?? rows.reduce((sum, row) => sum + row.count, 0)}</strong></div>
      <div><span>未识别</span><strong>{stats.unrecognized_events ?? "-"}</strong></div>
      <div><span>需状态建模</span><strong>{stats.needs_state_events ?? "-"}</strong></div>
      <div><span>默认目标数</span><strong>{stats.default_target_events ?? "-"}</strong></div>
    </div>
    <ReportTable className="coverage-table" columns={[
      { key: "category", label: "分类", render: (row) => row.classification?.category_label || row.classification?.category || "-" },
      { key: "name", label: "模拟技能名" }, { key: "raw_name", label: "CSV 原名" }, { key: "count", label: "次数" },
      { key: "targets", label: "目标/来源", render: (row) => `${row.max_targets ?? 1} / ${row.target_sources_text || "default"}` },
      { key: "tags_text", label: "标签" }, { key: "reason", label: "说明", render: (row) => row.classification?.reason || "-" },
    ]} rowClassName={(row) => row.classification?.category === "unrecognized" ? "danger-row" : row.classification?.needs_state || row.classification?.followup_unmodeled ? "warning-row" : ""} rows={rows} />
  </div>;
}

function PreviewTab({ result, rows }) {
  const meta = result?.preview?.meta || {};
  const previewRows = result?.preview?.rows || rows.slice(0, 20).map((row) => ({
    row_no: row.rowNo, time: row.time, name: row.action, raw_name: row.raw, is_gcd: row.isGcd,
    cast_time: row.castTime, targets: row.targets, target_source: row.targetSource, source: row.source,
  }));
  return <div className="view-stack">
    <div className="summary-band compact"><div><span>显示</span><strong>{previewRows.length} / {result?.preview?.total || rows.length}</strong></div><div><span>CSV 格式</span><strong>{meta.format || "本地预览"}</strong></div><div><span>castTime</span><strong>{meta.has_cast_time ? "有" : "无"}</strong></div><div><span>isGCD</span><strong>{meta.has_is_gcd ? "有" : "无"}</strong></div></div>
    <ReportTable columns={[
      { key: "row_no", label: "CSV行" }, { key: "time", label: "时间", render: (row) => fmt(row.time, 3) },
      { key: "name", label: "模拟技能名" }, { key: "raw_name", label: "CSV 原名" },
      { key: "is_gcd", label: "GCD", render: (row) => row.is_gcd === true ? "GCD" : row.is_gcd === false ? "oGCD" : "-" },
      { key: "cast_time", label: "读条", render: (row) => row.cast_time === null || row.cast_time === undefined ? "-" : fmt(row.cast_time, 2) },
      { key: "targets", label: "目标/来源", render: (row) => `${row.targets ?? 1} / ${row.target_source || "default"}` }, { key: "source", label: "来源" },
    ]} rows={previewRows} />
  </div>;
}

function OverviewTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  const meta = result.metadata || {};
  const panel = result.panel || {};
  const summary = result.summary || {};
  return <div className="overview-view">
    <div className="definition-band"><div><span className="status-dot" /><strong>{meta.resource_status || "报告就绪"}</strong></div><p>{result.definition}</p></div>
    <div className="metric-grid">
      <Metric label="期望 DPS / RD" value={fmt(summary.expected_dps, 2)} accent />
      <Metric label="标准差 σ" value={fmt(summary.std_dps, 2)} />
      <Metric label="最高 DPS" value={fmt(summary.max_dps, 2)} tone="green" />
      <Metric label="最低 DPS" value={fmt(summary.min_dps, 2)} tone="orange" />
      <Metric label="Top 1%" value={fmt(summary.top_1, 2)} />
      <Metric label="Top 0.1%" value={fmt(summary.top_0_1, 2)} />
      <Metric label="Top 0.01%" value={fmt(summary.top_0_01, 2)} />
      <Metric label="Bottom 1%" value={fmt(summary.bottom_1, 2)} />
    </div>
    <OverviewSection title="面板与理论数据"><KvGrid rows={[
      ["职业", meta.job_label || meta.job], ["主属性", `${panel.main_stat_name || "main"} ${panel.main_stat ?? "-"}`], ["武器性能", panel.weapon_damage],
      ["速度", `${panel.speed_stat_name || "speed"} ${panel.speed ?? "-"}`], ["暴击", `${panel.crit ?? "-"} -> ${pct((panel.crit_rate || 0) * 100, 3)} (x${fmt(panel.crit_damage, 3)})`],
      ["直击", `${panel.direct_hit ?? "-"} -> ${pct((panel.direct_hit_rate || 0) * 100, 3)}`], ["信念", panel.determination],
      ["GCD", `${seconds(panel.job_gcd)} (Base ${seconds(panel.base_gcd)})`], ["最后技能出伤", seconds(summary.last_hit)], ["有效战斗时长", seconds(summary.duration)],
    ]} /></OverviewSection>
    <OverviewSection title="输入与证据"><KvGrid rows={[
      ["生成时间", meta.generated_at], ["游戏版本", meta.game_version], ["技能数据", meta.skill_data_source], ["排轴样本", meta.csv_path],
      ["目标数来源", meta.target_source], ["不可选中轨道", meta.downtime_track_path || "未导入"], ["当前模式", meta.mode],
      ["全局上天", `${meta.global_downtime_count || 0} 段 / ${meta.global_downtime_source || "无"}`], ["模拟次数", meta.iterations], ["随机种子", meta.seed],
      ["导入冒烟", meta.import_smoke_passed], ["机制校准", meta.mechanic_calibrated], ["日志验证", meta.log_validated],
    ]} /></OverviewSection>
    <OverviewSection title={`资源合法性警告 (${result.resource_warnings?.length || 0})`}><ReportTable columns={[
      { key: "row_no", label: "CSV行" }, { key: "time", label: "时间", render: (row) => seconds(row.time) }, { key: "skill", label: "技能" },
      { key: "code", label: "代码" }, { key: "severity", label: "级别" }, { key: "message", label: "说明" },
    ]} rows={result.resource_warnings || []} /></OverviewSection>
    <OverviewSection title={`高 RD 模拟 (${result.high_rd_runs?.length || 0})`}><ReportTable columns={[
      { key: "run_id", label: "模拟序号" }, { key: "rd", label: "RD", render: (row) => fmt(row.rd, 2) }, { key: "duration", label: "有效时长", render: (row) => seconds(row.duration) },
    ]} rows={result.high_rd_runs || []} /></OverviewSection>
  </div>;
}

function Metric({ label, value, accent, tone = "" }) { return <div className={`metric-card ${accent ? "accent" : ""} ${tone}`}><span>{label}</span><strong>{value}</strong></div>; }
function OverviewSection({ title, children }) { return <section className="overview-section"><h3>{title}</h3>{children}</section>; }

function CombatLogTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  return <ReportTable className="combat-table" columns={[
    { key: "time", label: "Time (s)", render: (row) => fmt(row.time, 3) }, { key: "name", label: "Skill Name" },
    { key: "potency", label: "Potency" }, { key: "buffs", label: "Active Buffs" }, { key: "targets", label: "Targets" },
    { key: "crit", label: "Crit" }, { key: "dh", label: "DH" }, { key: "dmg", label: "Damage", render: (row) => Number.isFinite(Number(row.dmg)) ? fmt(row.dmg, 2) : row.dmg },
  ]} rows={result.combat_log || []} />;
}

function SkillDetailsTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  const rows = [...(result.skills || []), result.skill_total].filter(Boolean);
  return <ReportTable columns={[
    { key: "skill", label: "Skill Name" }, { key: "avg_cast_count", label: "Count", render: (row) => row.skill === "--- TOTAL ---" ? `${fmt(row.avg_cast_count, 1)} ± ${fmt(row.std_cast_count, 1)}` : fmt(row.avg_cast_count, 1) },
    { key: "avg_hits_per_cast", label: "Avg Hits", render: (row) => row.skill === "--- TOTAL ---" ? "-" : fmt(row.avg_hits_per_cast, 1) },
    { key: "avg_dps", label: "DPS (μ ± σ)", render: (row) => `${fmt(row.avg_dps, 2)} ± ${fmt(row.std_dps, 2)}` },
    { key: "crit_percent", label: "Crit %", render: (row) => row.skill === "--- TOTAL ---" ? "-" : pct(row.crit_percent) },
    { key: "direct_hit_percent", label: "DH %", render: (row) => row.skill === "--- TOTAL ---" ? "-" : pct(row.direct_hit_percent) },
    { key: "crit_direct_percent", label: "CDH %", render: (row) => row.skill === "--- TOTAL ---" ? "-" : pct(row.crit_direct_percent) },
  ]} rowClassName={(row) => row.skill === "--- TOTAL ---" ? "total-row blue" : ""} rows={rows} />;
}

function BestRunTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  const total = (result.best_run || []).reduce((sum, row) => sum + Number(row.damage || 0), 0);
  const rows = [...(result.best_run || []), ...(result.best_run?.length ? [{ skill: "--- MAX RUN TOTAL ---", damage: total, total: true }] : [])];
  return <ReportTable columns={[
    { key: "skill", label: "Skill Name" }, { key: "count", label: "Cast" }, { key: "hits", label: "Total Hits" },
    { key: "damage", label: "Total Damage", render: (row) => fmt(row.damage, 0) },
    { key: "crit_percent", label: "Crit %", render: (row) => row.total ? "-" : pct(row.crit_percent, 0) },
    { key: "direct_hit_percent", label: "DH %", render: (row) => row.total ? "-" : pct(row.direct_hit_percent, 0) },
    { key: "crit_direct_percent", label: "CDH %", render: (row) => row.total ? "-" : pct(row.crit_direct_percent, 0) },
  ]} rowClassName={(row) => row.total ? "total-row orange" : ""} rows={rows} />;
}

function IntervalsTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  return <ReportTable columns={[
    { key: "time", label: "时间节点", render: (row) => formatTime(row.time) },
    { key: "mean_rd", label: "RD (μ ± σ)", render: (row) => `${fmt(row.mean_rd, 2)} ± ${fmt(row.std_rd, 2)}` },
    { key: "max_rd", label: "Max RD", render: (row) => fmt(row.max_rd, 2) },
    { key: "top_1", label: "Top 1% (Z=2.326)", render: (row) => fmt(row.top_1, 2) },
    { key: "top_0_1", label: "Top 0.1% (Z=3.090)", render: (row) => fmt(row.top_0_1, 2) },
  ]} rows={result.intervals || []} />;
}

function DistributionTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  const rows = result.distribution || [];
  if (!rows.length) return <EmptyState />;
  const width = 960;
  const plot = { left: 72, right: 930, top: 42, bottom: 340 };
  const iterations = Number(result.metadata?.iterations) || rows.reduce((sum, row) => sum + row.count, 0);
  const lowerBounds = rows.map((row) => Number(row.range.split("-")[0]));
  const binSize = Number(rows[0].range.split("-")[1]) - lowerBounds[0] || 100;
  const mean = Number(result.summary.expected_dps);
  const std = Number(result.summary.std_dps);
  const thresholds = [
    [Number(result.summary.top_1), "Top 1%", "top1"],
    [Number(result.summary.top_0_1), "Top 0.1%", "top01"],
    [Number(result.summary.top_0_01), "Top 0.01%", "top001"],
  ];
  const domainMin = lowerBounds[0];
  const domainMax = Math.max(lowerBounds.at(-1) + binSize, ...thresholds.map(([value]) => value));
  const x = (value) => plot.left + (value - domainMin) / Math.max(1, domainMax - domainMin) * (plot.right - plot.left);
  const curve = std > 0 ? Array.from({ length: 161 }, (_, index) => {
    const value = domainMin + index / 160 * (domainMax - domainMin);
    const percent = Math.exp(-0.5 * ((value - mean) / std) ** 2) / (std * Math.sqrt(2 * Math.PI)) * 100 * binSize;
    return [value, percent];
  }) : [];
  const barPercents = rows.map((row) => row.count / iterations * 100);
  const rawMaxY = Math.max(...barPercents, ...curve.map((point) => point[1]), 1);
  const yMax = Math.max(5, Math.ceil(rawMaxY / 5) * 5);
  const y = (value) => plot.bottom - value / yMax * (plot.bottom - plot.top);
  const yTicks = Array.from({ length: 6 }, (_, index) => yMax / 5 * index);
  const xTickStep = Math.max(1, Math.ceil(rows.length / 7));
  const xTicks = lowerBounds.filter((_, index) => index % xTickStep === 0);
  if (xTicks.at(-1) !== lowerBounds.at(-1)) xTicks.push(lowerBounds.at(-1));
  const curvePath = curve.map(([value, percent], index) => `${index ? "L" : "M"}${x(value).toFixed(2)},${y(percent).toFixed(2)}`).join(" ");
  const barWidth = Math.max(3, x(domainMin + binSize) - x(domainMin) - 3);

  return <div className="distribution-view">
    <div className="chart-header"><div><span>DPS Distribution (N={iterations}, Bin={binSize})</span><strong>{fmt(mean, 2)} ± {fmt(std, 2)}</strong></div><div className="legend"><small><i className="legend-bar" />概率频次</small><small><i className="legend-normal" />正态分布</small><small><i className="legend-top1" />Top 1%</small><small><i className="legend-top01" />Top 0.1%</small><small><i className="legend-top001" />Top 0.01%</small></div></div>
    <svg className="distribution-chart" role="img" aria-label="DPS 分布概率图" viewBox={`0 0 ${width} 420`}>
      {yTicks.map((tick) => <g key={tick}><line className="chart-grid" x1={plot.left} x2={plot.right} y1={y(tick)} y2={y(tick)} /><text className="chart-label" textAnchor="end" x={plot.left - 10} y={y(tick) + 4}>{fmt(tick, tick % 1 ? 1 : 0)}%</text></g>)}
      {xTicks.map((tick) => <g key={tick}><line className="chart-axis" x1={x(tick)} x2={x(tick)} y1={plot.bottom} y2={plot.bottom + 5} /><text className="chart-label" textAnchor="middle" x={x(tick)} y={plot.bottom + 22}>{fmt(tick, 0)}</text></g>)}
      <line className="chart-axis" x1={plot.left} x2={plot.right} y1={plot.bottom} y2={plot.bottom} />
      <line className="chart-axis" x1={plot.left} x2={plot.left} y1={plot.top} y2={plot.bottom} />
      {rows.map((row, index) => {
        const percent = barPercents[index];
        return <g key={row.range}><rect className="distribution-bar" height={plot.bottom - y(percent)} rx="2" width={barWidth} x={x(lowerBounds[index]) + 1.5} y={y(percent)} /><title>{row.range}: {row.count} 次 / {fmt(percent, 2)}%</title></g>;
      })}
      {curvePath && <path className="normal-curve" d={curvePath} />}
      {thresholds.map(([value, label, tone], index) => <g key={label}><line className={`threshold-line ${tone}`} x1={x(value)} x2={x(value)} y1={plot.top} y2={plot.bottom} /><text className={`threshold-label ${tone}`} textAnchor="end" transform={`rotate(-90 ${x(value) - 5} ${plot.top + 72 + index * 12})`} x={x(value) - 5} y={plot.top + 72 + index * 12}>{label} {fmt(value, 0)}</text></g>)}
      <text className="chart-title-label" x={plot.left} y="22">Frequency (Probability %)</text>
      <text className="chart-title-label" textAnchor="end" x={plot.right} y="404">DPS / RD</text>
    </svg>
  </div>;
}

function DistributionTableTab({ result }) {
  if (!result?.summary) return <EmptyState needsRun />;
  return <ReportTable columns={[
    { key: "range", label: "DPS 区间" }, { key: "count", label: "频次" }, { key: "percent_ge", label: "上位占比 (≥Min)", render: (row) => pct(row.percent_ge, 2) },
  ]} rows={result.distribution || []} />;
}

export default App;
