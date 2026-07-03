# FFXIV Personal nDPS Modern UI

Run `ffxiv_personal_ndps_v2.exe` from this folder to open the React/Electron desktop UI.
Do not move or distribute only the exe; it needs the adjacent Electron runtime files and `resources` folder.

This package includes:

- the built modern UI under `resources\app`
- the packaged Python JSON backend under `resources\backend\ndps_backend.exe`
- the Electron runtime files required by the desktop shell
- post-run `[start, end)` time-window nDPS analysis without re-running simulation rolls

Use the legacy stable simulator GUI at `..\ffxiv_personal_ndps.exe` if you need the older Tk interface or command-line self-test.
