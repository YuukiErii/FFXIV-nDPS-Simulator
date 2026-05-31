const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");

const appRoot = app.isPackaged ? app.getAppPath() : path.resolve(__dirname, "..");
const repoRoot = app.isPackaged ? null : path.resolve(appRoot, "..", "..");
const bridgeScript = repoRoot ? path.join(repoRoot, "scripts", "run_ndps_simulation.py") : null;
const pythonExe = repoRoot ? path.join(repoRoot, ".venv", "Scripts", "python.exe") : null;
const packagedBackendExe = app.isPackaged
  ? path.join(process.resourcesPath, "backend", "ndps_backend.exe")
  : null;

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1120,
    minHeight: 760,
    title: "FFXIV Personal nDPS",
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

ipcMain.handle("ndps:run", async (_event, payload) => {
  if (!payload?.csv_path) {
    throw new Error("Choose an axis CSV before running simulation.");
  }

  const workDir = await fs.mkdtemp(path.join(os.tmpdir(), "ndps-ui-"));
  const inputPath = path.join(workDir, "input.json");
  const outputPath = path.join(workDir, "output.json");
  await fs.writeFile(inputPath, JSON.stringify(payload, null, 2), "utf8");

  await new Promise((resolve, reject) => {
    let stderr = "";
    const command = packagedBackendExe || pythonExe;
    const args = packagedBackendExe
      ? ["--input", inputPath, "--output", outputPath]
      : [bridgeScript, "--input", inputPath, "--output", outputPath];
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

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
