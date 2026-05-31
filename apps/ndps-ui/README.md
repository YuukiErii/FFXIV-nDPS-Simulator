# Modern nDPS UI

This is the high-ceiling UI track for `ffxiv_personal_ndps`: a React/Vite frontend that can later be wrapped by Electron or Tauri while keeping the validated Python simulator core intact.

Run locally:

```powershell
cd apps\ndps-ui
npm install
npm run dev
```

Desktop shell:

```powershell
npm run desktop
```

The current UI loads axis CSV files in-browser and renders the new dashboard, parameter surface, timeline preview, coverage-style classification, and result visualization shell. In Electron, the file picker keeps native paths and `Run Simulation` calls `scripts/run_ndps_simulation.py` through the preload bridge.
