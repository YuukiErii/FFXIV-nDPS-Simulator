# XIVShellTTS

`xiv_shell_tts.exe` converts a XIV in the Shell exported CSV into the TTS txt format used by the old `TTS.py` script.

Full workspace manual: `..\..\docs\USER_MANUAL.md`

Project status and evidence map: `..\..\docs\PROJECT_STATUS.md`

Input CSV should contain at least:

- `time`
- `action`

Output txt line format:

```text
-5.0 "<爆炎>~" tts "爆炎"
```

Use:

- Double-click `xiv_shell_tts.exe` to open the GUI.
- Select the exported CSV and press convert.
- Optional: select a fight timeline txt in `副本时间轴`; the app will also write a merged timeline txt.
- Or drag a CSV file onto `xiv_shell_tts.exe`; it writes `<input>_skillline.txt` and `<input>CN.csv` next to the CSV.
- CLI merge example:

```powershell
.\xiv_shell_tts.exe --convert .\axis.csv --out .\axis_skillline.txt --cn-csv .\axis_cn.csv --timeline .\fight_timeline.txt --merged-out .\axis_merged.txt
```

The converter uses `data/ff14_job_skill_en_cn_map.json`, generated from the full FF14 Chinese-English skill table. It keeps the old staged behavior: untranslated action names are preserved instead of being dropped.

Merge behavior follows the old `MERGE.PY` flow: read the fight timeline first, then the skill-line txt, parse an optional leading `#` plus the first numeric timestamp, and stable-sort all non-empty lines by that timestamp.

Rebuild from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_xiv_shell_tts_exe.ps1
```
