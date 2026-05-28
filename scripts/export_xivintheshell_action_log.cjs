const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const SITE_URL = "https://xivintheshell.com/";
const DEFAULT_CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";

function usage() {
  console.error(
    [
      "Usage:",
      "  node scripts/export_xivintheshell_action_log.cjs INPUT.json OUTPUT.csv [INPUT2.json OUTPUT2.csv ...]",
      "  node scripts/export_xivintheshell_action_log.cjs --with-damage INPUT.json ACTION.csv DAMAGE.csv [...]",
      "",
      "Set NODE_PATH to a Playwright node_modules directory if Playwright is not installed globally.",
    ].join("\n"),
  );
}

function abs(value) {
  return path.resolve(process.cwd(), value);
}

async function updateAndReadCsv(page) {
  return page.evaluate(async () => {
    const links = Array.from(document.querySelectorAll("a")).filter(
      (a) => a.download === "fight" && (a.textContent || "").toLowerCase().includes("csv"),
    );
    if (!links.length) {
      throw new Error("Could not find xivintheshell action-log CSV export link.");
    }
    const link = links[0];
    link.addEventListener("click", (event) => event.preventDefault(), {
      capture: true,
      once: true,
    });
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    await new Promise((resolve) => setTimeout(resolve, 500));
    return (await fetch(link.href)).text();
  });
}

async function updateAndReadDamageCsv(page) {
  return page.evaluate(async () => {
    const link = Array.from(document.querySelectorAll("a")).find(
      (a) => a.download === "damage-log" && (a.textContent || "").toLowerCase().includes("csv"),
    );
    if (!link) {
      throw new Error("Could not find xivintheshell damage-log CSV export link.");
    }
    link.addEventListener("click", (event) => event.preventDefault(), {
      capture: true,
      once: true,
    });
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    await new Promise((resolve) => setTimeout(resolve, 500));
    return (await fetch(link.href)).text();
  });
}

async function exportOne(browser, inputPath, outputPath, damageOutputPath) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  try {
    await page.goto(SITE_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(4000);
    const fileInputs = await page.locator('input[type="file"]').count();
    if (fileInputs < 1) {
      throw new Error("No file input found on xivintheshell page.");
    }
    await page.locator('input[type="file"]').nth(fileInputs - 1).setInputFiles(inputPath);
    await page.waitForTimeout(2500);
    const csv = await updateAndReadCsv(page);
    if (!csv.startsWith("time,action,isGCD,castTime")) {
      throw new Error(`Unexpected CSV header for ${inputPath}: ${csv.slice(0, 80)}`);
    }
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, csv, "utf8");
    const rows = csv.trimEnd().split(/\r?\n/).length - 1;
    let message = `${path.relative(process.cwd(), outputPath)}\t${rows}`;
    if (damageOutputPath) {
      const damageCsv = await updateAndReadDamageCsv(page);
      if (!damageCsv.startsWith("time,damageSource,potency")) {
        throw new Error(`Unexpected damage CSV header for ${inputPath}: ${damageCsv.slice(0, 80)}`);
      }
      fs.mkdirSync(path.dirname(damageOutputPath), { recursive: true });
      fs.writeFileSync(damageOutputPath, damageCsv, "utf8");
      const damageRows = damageCsv.trimEnd().split(/\r?\n/).length - 1;
      message += `\t${path.relative(process.cwd(), damageOutputPath)}\t${damageRows}`;
    }
    console.log(message);
  } finally {
    await page.close();
  }
}

async function main() {
  let args = process.argv.slice(2);
  const withDamage = args[0] === "--with-damage";
  if (withDamage) {
    args = args.slice(1);
  }
  const groupSize = withDamage ? 3 : 2;
  if (!args.length || args.length % groupSize !== 0) {
    usage();
    process.exit(2);
  }

  const executablePath = process.env.CHROME_EXECUTABLE || DEFAULT_CHROME;
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    for (let i = 0; i < args.length; i += groupSize) {
      await exportOne(
        browser,
        abs(args[i]),
        abs(args[i + 1]),
        withDamage ? abs(args[i + 2]) : undefined,
      );
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
