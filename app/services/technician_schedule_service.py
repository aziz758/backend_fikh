from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.technician import Technician


def parse_work_days(raw: str | None) -> set[int]:
    if not raw:
        return set()
    result: set[int] = set()
    for token in str(raw).split(","):
        item = token.strip()
        if not item:
            continue
        if not item.isdigit():
            continue
        day = int(item)
        if 0 <= day <= 6:
            result.add(day)
    return result


def serialize_work_days(days: list[int] | set[int]) -> str:
    normalized = sorted({int(day) for day in days if 0 <= int(day) <= 6})
    return ",".join(str(day) for day in normalized)


def _parse_time_hhmm(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    text = str(raw).strip()
    parts = text.split(":")
    if len(parts) != 2:
        return None
    if not parts[0].isdigit() or not parts[1].isdigit():
        return None
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour, minute


def resolve_service_radius_km(technician: Technician) -> float:
    radius = getattr(technician, "service_radius_km", None)
    if radius is None:
        return float(settings.TECHNICIAN_MAX_SERVICE_DISTANCE_KM)
    try:
        value = float(radius)
    except (TypeError, ValueError):
        value = float(settings.TECHNICIAN_MAX_SERVICE_DISTANCE_KM)
    return max(1.0, value)


def is_technician_within_working_hours(
    technician: Technician,
    *,
    now_utc: datetime | None = None,
) -> bool:
    """
    If no working-hours config exists, technician is considered available by schedule.
    Otherwise checks day + time in configured timezone.
    """
    days = parse_work_days(getattr(technician, "work_days", None))
    start = _parse_time_hhmm(getattr(technician, "work_start_time", None))
    end = _parse_time_hhmm(getattr(technician, "work_end_time", None))

    if not days and not start and not end:
        return True
    if not days or not start or not end:
        return False

    try:
        tz = ZoneInfo(settings.TECHNICIAN_WORKING_HOURS_TIMEZONE)
    except Exception:
        tz = ZoneInfo("UTC")

    current = (now_utc or datetime.utcnow()).replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    if current.weekday() not in days:
        return False

    current_minute = current.hour * 60 + current.minute
    start_minute = start[0] * 60 + start[1]
    end_minute = end[0] * 60 + end[1]

    if start_minute == end_minute:
        return True
    if start_minute < end_minute:
        return start_minute <= current_minute < end_minute
    return current_minute >= start_minute or current_minute < end_minute
