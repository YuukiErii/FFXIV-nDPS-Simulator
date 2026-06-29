import csv
import re


class AxisCsvError(ValueError):
    pass


_TTS_LINE_RE = re.compile(
    r'^\s*(?P<time>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s+.*?\btts\s+"(?P<name>[^"]+)"'
)


def _clean_header(value):
    return value.strip().lower().replace(" ", "").replace("_", "")


def _to_float(value, field_name, row_no):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise AxisCsvError(f"第 {row_no} 行的 {field_name} 不是数字: {value!r}") from exc


def _optional_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _optional_bool(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _nonempty_rows(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row_no, row in enumerate(csv.reader(f), 1):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) == 1 and row[0].strip().lower().startswith("sep="):
                continue
            yield row_no, [cell.strip() for cell in row]


def _find_header(rows):
    if not rows:
        raise AxisCsvError("CSV 文件为空。")
    row_no, row = rows[0]
    headers = [_clean_header(cell) for cell in row]
    if "time" in headers and "action" in headers:
        return row_no, {name: headers.index(name) for name in headers}, rows[1:]
    return None, {}, rows


def _entry(time_value, name, row_no, raw_name=None, is_gcd=None, cast_time=None,
           positional_hit=None, source="axis_csv"):
    action = (name or "").strip()
    if not action:
        raise AxisCsvError(f"第 {row_no} 行缺少 action/技能名。")
    return {
        "time": time_value,
        "name": action,
        "raw_name": (raw_name or action).strip(),
        "targets": 1,
        "is_gcd": is_gcd,
        "cast_time": cast_time,
        "positional_hit": positional_hit,
        "source": source,
        "row_no": row_no,
    }


def parse_axis_csv(path, normalize_name=None):
    normalize_name = normalize_name or (lambda value: value)
    rows = list(_nonempty_rows(path))
    header_row_no, columns, data_rows = _find_header(rows)
    entries = []
    skipped = 0
    tts_rows = 0

    if header_row_no is not None:
        time_idx = columns["time"]
        action_idx = columns["action"]
        is_gcd_idx = columns.get("isgcd")
        cast_idx = columns.get("casttime")
        positional_idx = columns.get("positionalhit", columns.get("positional"))
        for row_no, row in data_rows:
            if len(row) <= max(time_idx, action_idx):
                skipped += 1
                continue
            raw_name = row[action_idx]
            if not raw_name:
                skipped += 1
                continue
            entry = _entry(
                _to_float(row[time_idx], "time", row_no),
                normalize_name(raw_name),
                row_no,
                raw_name=raw_name,
                is_gcd=_optional_bool(row[is_gcd_idx]) if is_gcd_idx is not None and is_gcd_idx < len(row) else None,
                cast_time=_optional_float(row[cast_idx]) if cast_idx is not None and cast_idx < len(row) else None,
                positional_hit=(
                    _optional_bool(row[positional_idx])
                    if positional_idx is not None and positional_idx < len(row)
                    else None
                ),
            )
            entries.append(entry)
    else:
        for row_no, row in data_rows:
            if len(row) >= 2:
                raw_name = row[1]
                if not raw_name:
                    skipped += 1
                    continue
                entries.append(
                    _entry(
                        _to_float(row[0], "time", row_no),
                        normalize_name(raw_name),
                        row_no,
                        raw_name=raw_name,
                        source="positional_csv",
                    )
                )
                continue

            match = _TTS_LINE_RE.match(row[0])
            if match:
                raw_name = match.group("name")
                entries.append(
                    _entry(
                        _to_float(match.group("time"), "time", row_no),
                        normalize_name(raw_name),
                        row_no,
                        raw_name=raw_name,
                        source="tts_skillline_csv",
                    )
                )
                tts_rows += 1
            else:
                skipped += 1

    if not entries:
        name = str(path).lower()
        if "skillline" in name:
            raise AxisCsvError(
                "没有读到可模拟的技能行。这个文件名像 TTS skillline 文件，不是排轴网原始 CSV；"
                "已尝试按 TTS 行兼容解析，但没有找到形如 tts \"技能名\" 的行。"
                "建议优先选择包含 time/action 列的原始排轴 CSV。"
            )
        raise AxisCsvError("没有读到可模拟的技能行；请选择包含 time/action 列的排轴 CSV。")

    entries.sort(key=lambda item: item["time"])
    meta = {
        "rows": len(entries),
        "skipped": skipped,
        "format": "xiv_plan_csv" if header_row_no is not None else ("tts_skillline_csv" if tts_rows else "positional_csv"),
        "has_cast_time": any(item.get("cast_time") is not None for item in entries),
        "has_is_gcd": any(item.get("is_gcd") is not None for item in entries),
        "has_positional_hit": any(item.get("positional_hit") is not None for item in entries),
    }
    return entries, meta


def timeline_entry(item):
    if isinstance(item, dict):
        return item
    time_value, name, targets = item[:3]
    extra = item[3] if len(item) > 3 and isinstance(item[3], dict) else {}
    out = {"time": time_value, "name": name, "targets": targets}
    out.update(extra)
    return out


def timeline_time(item):
    return timeline_entry(item)["time"]


def timeline_name(item):
    return timeline_entry(item)["name"]


def timeline_targets(item):
    return int(timeline_entry(item).get("targets", 1))
