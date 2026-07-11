const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const { rmSync } = require("node:fs");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");

const appRoot = app.isPackaged ? app.getAppPath() : path.resolve(__dirname, "..");
const repoRoot = app.isPackaged ? null : path.resolve(appRoot, "..", "..");
const bridgeScript = repoRoot ? path.join(repoRoot, "scripts", "run_ndps_simulation.py") : null;
const pythonExe = repoRoot ? path.join(repoRoot, ".venv", "Scripts", "python.exe") : null;
const appIcon = app.isPackaged
  ? path.join(appRoot, "ffxiv_ndps.ico")
  : path.join(repoRoot, "src", "ffxiv_ndps_simulator", "ffxiv_ndps.ico");
const packagedBackendExe = app.isPackaged
  ? path.join(process.resourcesPath, "backend", "ndps_backend.exe")
  : null;
let activeWorkDir = null;
let completedWorkDir = null;
let completedWindowDataPath = null;

function cleanupWorkDir(workDir) {
  if (!workDir) return;
  try {
    rmSync(workDir, { recursive: true, force: true });
  } catch (error) {
    console.warn(`Could not remove simulator workspace ${workDir}:`, error);
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1520,
    height: 980,
    minWidth: 1180,
    minHeight: 800,
    title: "FFXIV Personal nDPS",
    icon: appIcon,
    backgroundColor: "#11100e",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    win.loadFile(path.join(appRoot, "dist", "index.html"));
  }
}

async function readPickedFile(filters) {
  const result = await dialog.showOpenDialog({
    properties: ["openFile"],
    filters,
  });
  if (result.canceled || !result.filePaths.length) {
    return null;
  }
  const filePath = result.filePaths[0];
  return {
    path: filePath,
    name: path.basename(filePath),
    text: await fs.readFile(filePath, "utf8"),
  };
}

ipcMain.handle("ndps:open-axis", () =>
  readPickedFile([{ name: "Axis CSV", extensions: ["csv", "txt"] }]),
);

ipcMain.handle("ndps:open-target", () =>
  readPickedFile([{ name: "Target JSON/TXT", extensions: ["json", "txt"] }]),
);

ipcMain.handle("ndps:open-track", () =>
  readPickedFile([{ name: "Untargetable track TXT", extensions: ["txt", "json"] }]),
);

ipcMain.handle("ndps:run", async (_event, payload) => {
  if (!payload?.csv_path) {
    throw new Error("Choose an axis CSV before running simulation.");
  }
  if (activeWorkDir) {
    throw new Error("A simulation is already running.");
  }

  const workDir = await fs.mkdtemp(path.join(os.tmpdir(), "ndps-ui-"));
  activeWorkDir = workDir;
  const inputPath = path.join(workDir, "input.json");
  const outputPath = path.join(workDir, "output.json");
  const windowDataPath = path.join(workDir, "window-data.bin");
  try {
    await fs.writeFile(inputPath, JSON.stringify(payload, null, 2), "utf8");

    await new Promise((resolve, reject) => {
      let stderr = "";
      const command = packagedBackendExe || pythonExe;
      const args = packagedBackendExe
        ? ["--input", inputPath, "--output", outputPath, "--window-data-output", windowDataPath]
        : [bridgeScript, "--input", inputPath, "--output", outputPath, "--window-data-output", windowDataPath];
      const child = spawn(command, args, {
        cwd: repoRoot || path.dirname(packagedBackendExe),
        windowsHide: true,
      });
      child.stderr.on("data", (chunk) => {
        stderr += chunk.toString();
      });
      child.on("error", reject);
      child.on("close", (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(stderr || `Simulation bridge exited with code ${code}`));
        }
      });
    });

    const result = JSON.parse(await fs.readFile(outputPath, "utf8"));
    cleanupWorkDir(completedWorkDir);
    completedWorkDir = workDir;
    completedWindowDataPath = windowDataPath;
    activeWorkDir = null;
    return result;
  } catch (error) {
    cleanupWorkDir(workDir);
    activeWorkDir = null;
    throw error;
  }
});

ipcMain.handle("ndps:analyze-window", async (_event, { start, end }) => {
  if (!completedWindowDataPath) throw new Error("Run a simulation before analyzing a time window.");
  const outputPath = path.join(path.dirname(completedWindowDataPath), "window-report.json");
  await new Promise((resolve, reject) => {
    let stderr = "";
    const command = packagedBackendExe || pythonExe;
    const commonArgs = [
      "--window-data-input", completedWindowDataPath,
      "--window-start", String(start), "--window-end", String(end), "--output", outputPath,
    ];
    const args = packagedBackendExe ? commonArgs : [bridgeScript, ...commonArgs];
    const child = spawn(command, args, {
      cwd: repoRoot || path.dirname(packagedBackendExe),
      windowsHide: true,
    });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolve() : reject(new Error(stderr || `Window analyzer exited with code ${code}`)));
  });
  return JSON.parse(await fs.readFile(outputPath, "utf8"));
});

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  cleanupWorkDir(activeWorkDir);
  cleanupWorkDir(completedWorkDir);
  activeWorkDir = null;
  completedWorkDir = null;
  completedWindowDataPath = null;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
