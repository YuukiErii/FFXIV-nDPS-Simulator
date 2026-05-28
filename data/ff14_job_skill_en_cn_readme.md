# FF14 Job Skill Chinese-English Mapping

Generated from client data CSVs aligned by action row ID.

Primary output:

- `ff14_job_skill_en_cn.csv`: unique PvE skill-name mapping, aggregated across jobs.
- `ff14_job_skill_en_cn_full.csv`: one row per source action ID, useful for tracing level, job, and sheet origin.
- `ff14_job_skill_en_cn_with_pvp.csv`: unique mapping with PvP actions included.
- `ff14_job_skill_en_cn_map.json`: simple `en_to_cn` and `cn_to_en` dictionaries from the PvE mapping.

Source CSVs are cached in `data/source/`.

- English data: `https://github.com/xivapi/ffxiv-datamining/tree/master/csv/en`
- Chinese data: `https://github.com/thewakingsands/ffxiv-datamining-cn`

Generation command:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_ff14_skill_translation.py
```

Filtering notes:

- Main CSV excludes PvP actions.
- `Action.csv` supplies combat, role, gathering, and related player/job actions.
- `CraftAction.csv` supplies crafting actions, which are not fully represented in `Action.csv`.
- Rows are aligned by source row ID; names are not manually translated.
