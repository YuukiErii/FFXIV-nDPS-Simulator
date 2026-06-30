import heapq
import json
import re


class SimEventType:
    PRESS = "press"
    DAMAGE = "damage"
    FOLLOWUP_DAMAGE = "followup_damage"
    DOT_TICK = "dot_tick"
    AUTO_ATTACK_CHECK = "aa_check"
    AUTO_ATTACK_DAMAGE = "aa_damage"
    SNAPSHOT = "snapshot"
    HISTORY_TICK = "history_tick"


SIM_EVENT_PRIORITY = {
    SimEventType.PRESS: 0,
    SimEventType.AUTO_ATTACK_CHECK: 1,
    SimEventType.DOT_TICK: 2,
    SimEventType.AUTO_ATTACK_DAMAGE: 3,
    SimEventType.DAMAGE: 3,
    SimEventType.FOLLOWUP_DAMAGE: 3,
    SimEventType.SNAPSHOT: 5,
    SimEventType.HISTORY_TICK: 5,
}


def push_sim_event(queue, event_time, event_type, tie_breaker, payload=None):
    heapq.heappush(
        queue,
        (
            float(event_time),
            SIM_EVENT_PRIORITY[event_type],
            event_type,
            next(tie_breaker),
            payload,
        ),
    )


def is_time_in_windows(t, windows, epsilon=1e-9):
    return any(start + epsilon < t < end - epsilon for start, end in windows)


def total_window_overlap(windows, end_time):
    total = 0.0
    for start, end in windows:
        if start < end_time:
            actual_end = min(end, end_time)
            if actual_end > start:
                total += actual_end - start
    return total


def parse_marker_track_downtime_windows(value):
    if not value:
        return []
    data = value
    if isinstance(value, str):
        text = value.strip().lstrip("\ufeff")
        if not text.startswith(("{", "[")):
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

    if isinstance(data, dict):
        if data.get("fileType") != "MarkerTrackIndividual" and "markers" not in data:
            return []
        markers = data.get("markers", [])
    elif isinstance(data, list):
        markers = data
    else:
        return []

    descriptions = [
        str(marker.get("description", "")).lower()
        for marker in markers
        if isinstance(marker, dict) and str(marker.get("description", "")).strip()
    ]
    require_untargetable_label = bool(descriptions)
    keywords = ("不可选中", "上天", "untargetable")

    windows = []
    for marker in markers:
        if not isinstance(marker, dict):
            continue
        description = str(marker.get("description", "")).lower()
        if require_untargetable_label and not any(keyword in description for keyword in keywords):
            continue
        try:
            start = float(marker["time"])
            if marker.get("duration") is not None:
                end = start + float(marker["duration"])
            else:
                end = float(marker["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if start < end:
            windows.append((start, end))
    return windows


def parse_downtime_windows(value):
    if not value:
        return []
    marker_windows = parse_marker_track_downtime_windows(value)
    if marker_windows:
        return marker_windows
    if isinstance(value, (list, tuple)):
        windows = []
        for item in value:
            if isinstance(item, dict):
                start, end = item.get("start"), item.get("end")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                start, end = item[0], item[1]
            else:
                continue
            windows.append((float(start), float(end)))
        return windows
    pairs = re.findall(r"(-?\d+(?:\.\d+)?)\s*(?:-|,|，|~|–|—)\s*(-?\d+(?:\.\d+)?)", str(value))
    return [(float(start), float(end)) for start, end in pairs if float(start) < float(end)]
