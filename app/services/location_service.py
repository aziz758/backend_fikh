from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.technician import Technician


def location_ttl_minutes() -> int:
    return max(1, settings.TECHNICIAN_LOCATION_TTL_MINUTES)


def location_cutoff_utc(*, now: datetime | None = None) -> datetime:
    current = now or datetime.utcnow()
    return current - timedelta(minutes=location_ttl_minutes())


def is_technician_location_fresh(technician: Technician, *, now: datetime | None = None) -> bool:
    if technician.lat is None or technician.lng is None:
        return False
    if technician.location_updated_at is None:
        return False
    return technician.location_updated_at >= location_cutoff_utc(now=now)


def sync_technician_availability_with_location(
    technician: Technician,
    *,
    now: datetime | None = None,
) -> str | None:
    """
    Keep availability aligned with location freshness policy.
    - approved + fresh location + offline/None => available
    - approved + stale/missing location + available/None => offline
    - explicit statuses like busy/on_break are preserved
    """
    if technician.status != "approved":
        return technician.availability_status

    is_fresh = is_technician_location_fresh(technician, now=now)
    if is_fresh:
        if technician.availability_status in (None, "offline"):
            technician.availability_status = "available"
        return technician.availability_status

    if technician.availability_status in (None, "available"):
        technician.availability_status = "offline"
    return technician.availability_status


def mark_stale_available_technicians_offline(
    db: Session,
    *,
    now: datetime | None = None,
) -> int:
    cutoff = location_cutoff_utc(now=now)
    updated = (
        db.query(Technician)
        .filter(
            Technician.status == "approved",
            Technician.availability_status == "available",
            or_(
                Technician.location_updated_at.is_(None),
                Technician.location_updated_at < cutoff,
                Technician.lat.is_(None),
                Technician.lng.is_(None),
            ),
        )
        .update({"availability_status": "offline"}, synchronize_session=False)
    )
    return int(updated or 0)
