import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Download,
  FileText,
  Gauge,
  Play,
  Settings2,
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

const MAIN_STAT_DEFAULTS = {
  NIN: 6490,
};

const DEFAULT_STATS = {
  mainStat: 6498,
  crt: 3605,
  det: 2426,
  dh: 1793,
  sks: 689,
  wd: 158,
  delay: 2.64,
  partyBonus: 1.05,
  version: 7.5,
  iterations: 1000,
  threshold: 46000,
};

const DEFAULT_SIM_OPTIONS = {
  globalDowntime: "",
  customSnaps: "",
  multiBossMode: false,
  downtimeConfig: "",
  dotConfig: "",
};

const SAMPLE_ROWS = [
  { time: 0.0, action: "Gyofu", raw: "Gyofu", source: "sample" },
  { time: 2.14, action: "Jinpu", raw: "Jinpu", source: "sample" },
  { time: 4.28, action: "Gekko", raw: "Gekko", source: "sample" },
  { time: 6.42, action: "Higanbana", raw: "Higanbana", source: "sample" },
  { time: 9.04, action: "Meikyo Shisui", raw: "Meikyo Shisui", source: "sample" },
  { time: 10.35, action: "Kasha", raw: "Kasha", source: "sample" },
  { time: 12.49, action: "Yukikaze", raw: "Yukikaze", source: "sample" },
  { time: 14.63, action: "Midare Setsugekka", raw: "Midare Setsugekka", source: "sample" },
  { time: 15.25, action: "Kaeshi: Setsugekka", raw: "Kaeshi: Setsugekka", source: "sample" },
  { time: 16.72, action: "Tendo Setsugekka", raw: "Tendo Setsugekka", source: "sample" },
  { time: 18.03, action: "Tendo Kaeshi Setsugekka", raw: "Tendo Kaeshi Setsugekka", source: "sample" },
];

const DOT_HINTS = ["Higanbana", "Caustic Bite", "Stormbite", "Biolysis", "Thunder", "High Thunder"];
const BUFF_HINTS = [
  "Meikyo",
  "Tincture",
  "Battle Voice",
  "Embolden",
  "Arcane Circle",
  "Technical",
  "Devilment",
  "Ley Lines",
  "Hypercharge",
  "Wildfire",
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
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}

function parseAxisCsv(text) {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.toLowerCase().startsWith("sep="));

  if (!lines.length) return [];

  const first = parseCsvLine(lines[0]);
  const normalized = first.map((cell) => cell.toLowerCase().replace(/[\s_]/g, ""));
  const hasHeader = normalized.includes("time") && normalized.includes("action");
  const timeIndex = hasHeader ? normalized.indexOf("time") : 0;
  const actionIndex = hasHeader ? normalized.indexOf("action") : 1;
  const rows = hasHeader ? lines.slice(1) : lines;

  return rows
    .map((line, offset) => {
      const cells = parseCsvLine(line);
      if (cells.length <= Math.max(timeIndex, actionIndex)) return null;
      const time = Number.parseFloat(cells[timeIndex]);
      const action = cells[actionIndex];
      if (!Number.isFinite(time) || !action) return null;
      return {
        time,
        action,
        raw: action,
        source: hasHeader ? "xiv_plan_csv" : "positional_csv",
        rowNo: offset + (hasHeader ? 2 : 1),
      };
    })
    .filter(Boolean)
    .sort((left, right) => left.time - right.time);
}

function classifyRow(row) {
  const name = row.action;
  if (DOT_HINTS.some((hint) => name.includes(hint))) return "dot";
  if (BUFF_HINTS.some((hint) => name.includes(hint))) return "buff";
  if (/Sprint|Feint|Addle|Second Wind|True North|Arms Length|Lucid/.test(name)) return "utility";
  return "damage";
}

function summarizeRows(rows) {
  const duration = rows.length ? Math.max(...rows.map((row) => row.time)) : 0;
  const uniqueSkills = new Set(rows.map((row) => row.action)).size;
  const counts = rows.reduce(
    (acc, row) => {
      acc[classifyRow(row)] += 1;
      return acc;
    },
    { damage: 0, dot: 0, buff: 0, utility: 0 },
  );
  return { duration, uniqueSkills, counts };
}

function buildProjection(rows, stats) {
  const summary = summarizeRows(rows);
  const activeRows = Math.max(1, rows.length);
  const duration = Math.max(1, summary.duration);
  const statFactor =
    stats.mainStat * 0.36 +
    stats.crt * 0.08 +
    stats.det * 0.05 +
    stats.dh * 0.045 +
    stats.wd * 95 +
    activeRows * 22;
  const expected = Math.round((statFactor / duration) * 108);
  const spread = Math.max(420, Math.round(expected * 0.034));
  const distribution = Array.from({ length: 18 }, (_, index) => {
    const x = -2.6 + index * 0.31;
    const curve = Math.exp(-0.5 * x * x);
    const wave = 0.82 + 0.18 * Math.sin(index * 1.7 + activeRows);
    return Math.round(curve * wave * 100);
  });
  const timeline = rows.slice(0, 34).map((row, index) => ({
    time: row.time,
    value: Math.round(expected * (0.72 + index / Math.max(14, rows.length) * 0.34)),
    action: row.action,
  }));
  return {
    expected,
    spread,
    high: expected + Math.round(spread * 2.326),
    peak: expected + Math.round(spread * 3.09),
    distribution,
    timeline,
  };
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return `${minutes}:${rest.toFixed(rest % 1 === 0 ? 0 : 1).padStart(2, "0")}`;
}

function formatWindowNumber(value) {
  return Number.parseFloat(value.toFixed(3)).toString();
}

function downtimeTextFromPairs(text) {
  const matches = Array.from(String(text || "").matchAll(/(-?\d+(?:\.\d+)?)\s*(?:-|,|，|~|–|—)\s*(-?\d+(?:\.\d+)?)/g));
  return matches
    .map((match) => [Number.parseFloat(match[1]), Number.parseFloat(match[2])])
    .filter(([start, end]) => Number.isFinite(start) && Number.isFinite(end) && start < end)
    .map(([start, end]) => `${formatWindowNumber(start)}-${formatWindowNumber(end)}`)
    .join(", ");
}

function markerTrackDowntimeText(text) {
  let data;
  try {
    data = JSON.parse(String(text || "").replace(/^\uFEFF/, "").trim());
  } catch {
    return downtimeTextFromPairs(text);
  }
  if (!data || (data.fileType !== "MarkerTrackIndividual" && !Array.isArray(data.markers))) return "";
  const markers = Array.isArray(data.markers) ? data.markers : [];
  const descriptions = markers.map((marker) => String(marker?.description || "").toLowerCase()).filter(Boolean);
  const needsLabel = descriptions.length > 0;
  const keywords = ["不可选中", "上天", "untargetable"];
  return markers
    .filter((marker) => !needsLabel || keywords.some((keyword) => String(marker?.description || "").toLowerCase().includes(keyword)))
    .map((marker) => [Number.parseFloat(marker?.time), Number.parseFloat(marker?.duration)])
    .filter(([start, duration]) => Number.isFinite(start) && Number.isFinite(duration) && duration > 0)
    .map(([start, duration]) => `${formatWindowNumber(start)}-${formatWindowNumber(start + duration)}`)
    .join(", ");
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

  const summary = useMemo(() => summarizeRows(rows), [rows]);
  const fallbackProjection = useMemo(() => buildProjection(rows, stats), [rows, stats]);
  const hasSimulation = Boolean(runResult?.summary);
  const projection = useMemo(() => {
    if (!runResult?.summary) return fallbackProjection;
    return {
      ...fallbackProjection,
      expected: Math.round(runResult.summary.expected_dps),
      spread: Math.round(runResult.summary.std_dps),
      high: Math.round(runResult.summary.top_1),
      peak: Math.round(runResult.summary.top_0_1),
    };
  }, [fallbackProjection, runResult]);
  const coverageRows = useMemo(
    () =>
      rows.slice(0, 80).map((row) => ({
        ...row,
        category: classifyRow(row),
      })),
    [rows],
  );

  async function readAxisFile(file) {
    if (!file) return;
    const text = typeof file.text === "function" ? await file.text() : file.text || "";
    const parsed = parseAxisCsv(text);
    if (!parsed.length) {
      setStatus("error");
      return;
    }
    setRows(parsed);
    setAxisFile({ name: file.name, path: file.path || "", text });
    setStatus("ready");
    setRunResult(null);
    setRunError("");
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
    const downtimeText = markerTrackDowntimeText(text);
    if (downtimeText) {
      setSimOptions((current) => ({ ...current, globalDowntime: downtimeText }));
    }
  }

  function updateStat(key, value) {
    setStats((current) => ({
      ...current,
      [key]: Number.parseFloat(value) || 0,
    }));
  }

  function updateSimOption(key, value) {
    setSimOptions((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function parseNumberList(value) {
    return String(value || "")
      .replace(/，/g, ",")
      .split(",")
      .map((item) => Number.parseFloat(item.trim()))
      .filter((item) => Number.isFinite(item));
  }

  function exportUiSnapshot() {
    const payload = {
      source: axisFile?.name || "sample",
      target: targetFile?.name || "",
      track: trackFile?.name || "",
      job,
      stats,
      simOptions,
      rows: rows.length,
      summary,
      projection,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ndps-ui-snapshot.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function chooseAxis() {
    if (window.ndps?.openAxis) {
      const file = await window.ndps.openAxis();
      if (file) await readAxisFile(file);
      return;
    }
    axisInputRef.current?.click();
  }

  async function chooseTarget() {
    if (window.ndps?.openTarget) {
      const file = await window.ndps.openTarget();
      if (file) await readTargetFile(file);
      return;
    }
    targetInputRef.current?.click();
  }

  async function chooseTrack() {
    if (window.ndps?.openTrack) {
      const file = await window.ndps.openTrack();
      if (file) await readTrackFile(file);
      return;
    }
    trackInputRef.current?.click();
  }

  async function runSimulation() {
    setRunError("");
    if (!window.ndps?.runSimulation) {
      setStatus("preview");
      return;
    }
    if (!axisFile?.path) {
      setRunError("Choose an axis CSV through the desktop file picker before running the Python simulator.");
      return;
    }
    setIsRunning(true);
    try {
      const result = await window.ndps.runSimulation({
        csv_path: axisFile.path,
        target_path: targetFile?.path || "",
        downtime_track_path: trackFile?.path || "",
        job,
        iterations: Math.max(1, Math.trunc(stats.iterations)),
        threshold: stats.threshold,
        global_downtime: simOptions.globalDowntime,
        custom_snaps: parseNumberList(simOptions.customSnaps),
        multi_boss_mode: simOptions.multiBossMode,
        downtime_config: simOptions.downtimeConfig,
        dot_config: simOptions.dotConfig,
        stats: {
          main_stat: stats.mainStat,
          crt: stats.crt,
          det: stats.det,
          dh: stats.dh,
          sks: stats.sks,
          wd: stats.wd,
          delay: stats.delay,
          party_bonus: stats.partyBonus,
          version: String(stats.version),
        },
      });
      setRunResult(result);
      setStatus("simulated");
      setActiveTab("results");
    } catch (error) {
      setRunError(error?.message || String(error));
      setStatus("error");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-mark">
            <Swords size={22} />
          </div>
          <div>
            <p className="eyebrow">Personal nDPS</p>
            <h1>FFXIV Simulator</h1>
          </div>
        </div>

        <section className="control-section">
          <div className="section-heading">
            <Settings2 size={16} />
            <span>Job</span>
          </div>
          <div className="job-grid">
            {JOBS.map((item) => (
              <button
                className={item === job ? "job-button active" : "job-button"}
                key={item}
                onClick={() => {
                  setJob(item);
                  setStats((current) => ({
                    ...current,
                    delay: WEAPON_DELAYS[item] ?? current.delay,
                    mainStat: MAIN_STAT_DEFAULTS[item] ?? DEFAULT_STATS.mainStat,
                  }));
                }}
                type="button"
              >
                {item}
              </button>
            ))}
          </div>
        </section>

        <section className="control-section">
          <div className="section-heading">
            <Gauge size={16} />
            <span>Stats</span>
          </div>
          <div className="stat-grid">
            {[
              ["mainStat", "Main"],
              ["crt", "CRT"],
              ["det", "DET"],
              ["dh", "DHT"],
              ["sks", "SKS/SPS"],
              ["wd", "WD"],
              ["delay", "Delay"],
              ["partyBonus", "Party"],
              ["version", "Patch"],
              ["iterations", "Runs"],
              ["threshold", "RD Gate"],
            ].map(([key, label]) => (
              <label className="field" key={key}>
                <span>{label}</span>
                <input value={stats[key]} onChange={(event) => updateStat(key, event.target.value)} />
              </label>
            ))}
          </div>
        </section>

        <section className="control-section">
          <div className="section-heading">
            <Timer size={16} />
            <span>Fight Rules</span>
          </div>
          <div className="rules-grid">
            <label className="field wide">
              <span>Global downtime</span>
              <input
                placeholder="60-75, 180-195"
                value={simOptions.globalDowntime}
                onChange={(event) => updateSimOption("globalDowntime", event.target.value)}
              />
            </label>
            <label className="field wide">
              <span>Custom snapshots</span>
              <input
                placeholder="60, 120.5, 300"
                value={simOptions.customSnaps}
                onChange={(event) => updateSimOption("customSnaps", event.target.value)}
              />
            </label>
            <label className="toggle-field">
              <input
                checked={simOptions.multiBossMode}
                onChange={(event) => updateSimOption("multiBossMode", event.target.checked)}
                type="checkbox"
              />
              <span>Multi boss / split DoT mode</span>
            </label>
            <label className="field wide">
              <span>Target downtime</span>
              <textarea
                placeholder="T1:60-75; T2:120-135"
                value={simOptions.downtimeConfig}
                onChange={(event) => updateSimOption("downtimeConfig", event.target.value)}
              />
            </label>
            <label className="field wide">
              <span>DoT target plan</span>
              <textarea
                placeholder="Higanbana:1,2; Caustic Bite:1,2"
                value={simOptions.dotConfig}
                onChange={(event) => updateSimOption("dotConfig", event.target.value)}
              />
            </label>
          </div>
        </section>

        <section className="control-section compact">
          <button className="primary-action" onClick={runSimulation} type="button">
            <Play size={17} />
            <span>{isRunning ? "Running..." : "Run Simulation"}</span>
          </button>
          <button className="secondary-action" onClick={exportUiSnapshot} type="button">
            <Download size={17} />
            <span>Export Snapshot</span>
          </button>
        </section>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h2>{axisFile?.name || "Sample Axis"}</h2>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" onClick={chooseAxis} type="button" title="Import axis CSV">
              <Upload size={18} />
              <span>Axis CSV</span>
            </button>
            <button className="icon-button" onClick={chooseTarget} type="button" title="Import target JSON/TXT">
              <FileText size={18} />
              <span>Target TXT</span>
            </button>
            <button className="icon-button" onClick={chooseTrack} type="button" title="Import untargetable track TXT">
              <Timer size={18} />
              <span>Track TXT</span>
            </button>
            <input
              accept=".csv,text/csv"
              hidden
              onChange={(event) => readAxisFile(event.target.files?.[0])}
              ref={axisInputRef}
              type="file"
            />
            <input
              accept=".txt,.json,application/json,text/plain"
              hidden
              onChange={(event) => readTargetFile(event.target.files?.[0])}
              ref={targetInputRef}
              type="file"
            />
            <input
              accept=".txt,.json,application/json,text/plain"
              hidden
              onChange={(event) => readTrackFile(event.target.files?.[0])}
              ref={trackInputRef}
              type="file"
            />
          </div>
        </header>

        <section className="hero-grid">
          <div className="run-card">
            <div className="status-line">
              {status === "error" ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
              <span>
                {status === "sample"
                  ? "Sample data loaded"
                  : status === "error"
                    ? "Needs attention"
                    : status === "simulated"
                      ? "Python simulation complete"
                      : "Axis ready"}
              </span>
            </div>
            <div className="run-metric">
              <span>{projection.expected.toLocaleString()}</span>
              <small>{hasSimulation ? "Expected RD" : "Preview RD"}</small>
            </div>
            <div className="sparkline" aria-label="RD timeline">
              <TimelineSvg data={projection.timeline} />
            </div>
          </div>

          <MetricCard icon={<Activity size={18} />} label="Rows" value={rows.length.toLocaleString()} detail={`${summary.uniqueSkills} unique`} />
          <MetricCard icon={<Timer size={18} />} label="Duration" value={formatTime(summary.duration)} detail={`${summary.duration.toFixed(1)}s`} />
          <MetricCard icon={<Zap size={18} />} label="Top 1%" value={projection.high.toLocaleString()} detail={`std ${projection.spread.toLocaleString()}`} />
        </section>

        <section className="file-strip">
          <DropPanel
            file={axisFile}
            icon={<Upload size={19} />}
            label="Axis CSV"
            onClick={chooseAxis}
            onDrop={readAxisFile}
          />
          <DropPanel
            file={targetFile}
            icon={<FileText size={19} />}
            label="Target TXT"
            onClick={chooseTarget}
            onDrop={readTargetFile}
          />
          <DropPanel
            file={trackFile}
            icon={<Timer size={19} />}
            label="Track TXT"
            onClick={chooseTrack}
            onDrop={readTrackFile}
          />
          <div className="confidence-panel">
            <span className="signal good" />
            <div>
              <strong>{summary.counts.damage + summary.counts.dot} damage rows</strong>
              <small>{summary.counts.buff} buffs, {summary.counts.utility} utility rows</small>
            </div>
          </div>
        </section>

        <nav className="tabbar" aria-label="Result views">
          {[
            ["coverage", "Coverage", Table2],
            ["timeline", "Timeline", Timer],
            ["results", "Results", BarChart3],
            ["log", "Combat Log", Activity],
          ].map(([key, label, Icon]) => (
            <button className={activeTab === key ? "tab active" : "tab"} key={key} onClick={() => setActiveTab(key)} type="button">
              <Icon size={16} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <section className="panel-surface">
          {runError && (
            <div className="error-banner">
              <AlertTriangle size={17} />
              <span>{runError}</span>
            </div>
          )}
          {activeTab === "coverage" && <CoverageTable rows={coverageRows} />}
          {activeTab === "timeline" && <TimelineTable rows={rows} />}
          {activeTab === "results" && <ResultsPanel projection={projection} runResult={runResult} />}
          {activeTab === "log" && <CombatLog rows={rows} projection={projection} />}
        </section>
      </main>
    </div>
  );
}

function MetricCard({ icon, label, value, detail }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function DropPanel({ file, icon, label, onClick, onDrop }) {
  return (
    <button
      className="drop-panel"
      onClick={onClick}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        onDrop(event.dataTransfer.files?.[0]);
      }}
      type="button"
    >
      {icon}
      <span>{label}</span>
      <strong>{file?.name || "No file"}</strong>
    </button>
  );
}

function CoverageTable({ rows }) {
  return (
    <div className="data-table">
      <div className="table-row table-head">
        <span>Class</span>
        <span>Time</span>
        <span>Skill</span>
        <span>Source</span>
      </div>
      {rows.map((row, index) => (
        <div className="table-row" key={`${row.time}-${row.action}-${index}`}>
          <span className={`pill ${row.category}`}>{row.category}</span>
          <span>{row.time.toFixed(2)}</span>
          <strong>{row.action}</strong>
          <span>{row.source}</span>
        </div>
      ))}
    </div>
  );
}

function TimelineTable({ rows }) {
  return (
    <div className="timeline-list">
      {rows.slice(0, 70).map((row, index) => (
        <div className="timeline-item" key={`${row.time}-${row.action}-${index}`}>
          <span>{formatTime(row.time)}</span>
          <strong>{row.action}</strong>
          <small>{row.raw}</small>
        </div>
      ))}
    </div>
  );
}

function ResultsPanel({ projection, runResult }) {
  const skillRows = runResult?.skills?.slice(0, 8) || [];
  if (!runResult?.summary) {
    return (
      <div className="empty-state">
        <strong>Python simulation has not run.</strong>
        <span>Use the desktop file picker, then run the simulation to show real RD.</span>
      </div>
    );
  }
  return (
    <div className="results-grid">
      <div className="chart-panel">
        <div className="panel-title">
          <BarChart3 size={17} />
          <span>DPS Distribution</span>
        </div>
        <DistributionSvg values={projection.distribution} />
      </div>
      <div className="result-stack">
        <ResultLine label="Expected RD" value={projection.expected} />
        <ResultLine label="Top 1%" value={projection.high} />
        <ResultLine label="Top 0.1%" value={projection.peak} />
        {skillRows.length > 0 && (
          <div className="skill-mini-list">
            {skillRows.map((row) => (
              <div key={row.skill}>
                <span>{row.skill}</span>
                <strong>{Math.round(row.avg_dps).toLocaleString()}</strong>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ResultLine({ label, value }) {
  return (
    <div className="result-line">
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}

function CombatLog({ rows, projection }) {
  return (
    <div className="data-table log-table">
      <div className="table-row table-head">
        <span>Time</span>
        <span>Skill</span>
        <span>Projected RD</span>
      </div>
      {rows.slice(0, 60).map((row, index) => (
        <div className="table-row" key={`${row.time}-${row.action}-${index}`}>
          <span>{row.time.toFixed(2)}</span>
          <strong>{row.action}</strong>
          <span>{Math.round(projection.expected * (0.74 + index / Math.max(16, rows.length) * 0.24)).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function DistributionSvg({ values }) {
  const max = Math.max(...values, 1);
  return (
    <svg className="bar-chart" viewBox="0 0 560 220" role="img" aria-label="DPS distribution bars">
      <line x1="22" x2="538" y1="188" y2="188" className="axis" />
      {values.map((value, index) => {
        const width = 22;
        const gap = 7;
        const height = (value / max) * 146;
        const x = 32 + index * (width + gap);
        const y = 188 - height;
        return <rect className="bar" height={height} key={index} rx="4" width={width} x={x} y={y} />;
      })}
      <text x="32" y="208">low</text>
      <text x="486" y="208">high</text>
    </svg>
  );
}

function TimelineSvg({ data }) {
  if (!data.length) return null;
  const max = Math.max(...data.map((point) => point.value), 1);
  const points = data
    .map((point, index) => {
      const x = 8 + (index / Math.max(1, data.length - 1)) * 304;
      const y = 74 - (point.value / max) * 58;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 320 86" role="img" aria-label="RD sparkline">
      <polyline className="spark-area" points={`8,78 ${points} 312,78`} />
      <polyline className="spark-line" points={points} />
    </svg>
  );
}

export default App;
