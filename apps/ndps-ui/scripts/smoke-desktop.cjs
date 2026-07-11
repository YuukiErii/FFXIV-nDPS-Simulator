const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const electronPath = require("electron");
const { _electron: electron } = require("playwright-core");

const appRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(appRoot, "..", "..");
const tempPrefix = "ndps-ui-";
const packaged = process.argv.includes("--packaged");

function tempWorkspaces() {
  return new Set(fs.readdirSync(os.tmpdir()).filter((name) => name.startsWith(tempPrefix)));
}

async function main() {
  if (!packaged && !fs.existsSync(path.join(appRoot, "dist", "index.html"))) {
    throw new Error("Build the frontend with `npm run build` before running the desktop smoke test.");
  }

  const before = tempWorkspaces();
  const packagedExe = path.join(repoRoot, "releases", "windows", "ffxiv_personal_ndps_modern", "ffxiv_personal_ndps_v2.exe");
  const electronApp = await electron.launch({
    executablePath: packaged ? packagedExe : electronPath,
    args: packaged ? [] : [path.join(appRoot, "electron", "main.cjs")],
    cwd: appRoot,
  });

  try {
    const page = await electronApp.firstWindow();
    const payload = {
      csv_path: path.join(repoRoot, "examples", "skill_lines", "brd_xivintheshell_smoke", "brd_xivintheshell_smoke.csv"),
      job: "BRD",
      iterations: 2,
      seed: 12345,
    };
    const result = await page.evaluate((input) => window.ndps.runSimulation(input), payload);
    if (!(result?.summary?.expected_dps > 0) || result?.metadata?.iterations !== 2) {
      throw new Error("Desktop simulation did not return a valid two-iteration report.");
    }

    const windowReport = await page.evaluate(
      ([start, end]) => window.ndps.analyzeWindow(start, end),
      [0, result.summary.last_hit],
    );
    if (!(windowReport?.summary?.expected_dps > 0)) {
      throw new Error("Desktop window analysis did not return positive DPS.");
    }

    let rejected = false;
    try {
      await page.evaluate((input) => window.ndps.runSimulation(input), { ...payload, iterations: 0 });
    } catch (error) {
      rejected = String(error).includes("at least 1");
    }
    if (!rejected) {
      throw new Error("Desktop backend accepted a non-positive iteration count.");
    }
  } finally {
    await electronApp.close();
  }

  await new Promise((resolve) => setTimeout(resolve, 200));
  const leaked = [...tempWorkspaces()].filter((name) => !before.has(name));
  if (leaked.length) {
    throw new Error(`Desktop smoke leaked temporary workspaces: ${leaked.join(", ")}`);
  }
  console.log(`modern ${packaged ? "packaged" : "source"} desktop smoke ok`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
