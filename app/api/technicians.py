from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Rating, Request as RequestModel, Technician, TechnicianService
from app.services.location_service import location_cutoff_utc, mark_stale_available_technicians_offline
from app.services.technician_priority_service import compute_technician_priority_score
from app.services.technician_schedule_service import (
    is_technician_within_working_hours,
    parse_work_days,
    resolve_service_radius_km,
)

router = APIRouter(prefix="/technicians", tags=["technicians"])
TECHNICIAN_ACTIVE_REQUEST_STATUSES = ("accepted",)


def haversine_distance(lat1, lng1, lat2, lng2):
    """Approximate distance in kilometers."""
    import math

    r = 6371
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return r * c


@router.get("/nearby")
def get_nearby_technicians(
    service_id: int = Query(...),
    customer_lat: float = Query(...),
    customer_lng: float = Query(...),
    limit: int = Query(10, le=50),
    max_distance_km: float | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """Get nearby technicians ranked by priority score."""
    effective_max_distance_km = (
        float(max_distance_km)
        if max_distance_km is not None
        else float(settings.TECHNICIAN_MAX_SERVICE_DISTANCE_KM)
    )
    cutoff = location_cutoff_utc()
    updated = mark_stale_available_technicians_offline(db)
    if updated > 0:
        db.commit()

    active_request_exists = (
        db.query(RequestModel.id)
        .filter(
            RequestModel.assigned_technician_id == Technician.id,
            RequestModel.status.in_(TECHNICIAN_ACTIVE_REQUEST_STATUSES),
        )
        .exists()
    )
    subq = (
        db.query(Rating.technician_id, func.avg(Rating.score).label("avg_rating"))
        .group_by(Rating.technician_id)
        .subquery()
    )
    techs = (
        db.query(Technician)
        .join(TechnicianService, TechnicianService.technician_id == Technician.id)
        .outerjoin(subq, subq.c.technician_id == Technician.id)
        .filter(
            TechnicianService.service_id == service_id,
            Technician.status == "approved",
            or_(Technician.availability_status == "available", Technician.availability_status.is_(None)),
            Technician.lat.isnot(None),
            Technician.lng.isnot(None),
            Technician.location_updated_at.isnot(None),
            Technician.location_updated_at >= cutoff,
            ~active_request_exists,
        )
        .all()
    )
    result = []
    for technician in techs:
        if not is_technician_within_working_hours(technician):
            continue
        dist = (
            haversine_distance(customer_lat, customer_lng, technician.lat, technician.lng)
            if technician.lat is not None and technician.lng is not None
            else None
        )
        technician_radius = min(resolve_service_radius_km(technician), effective_max_distance_km)
        if dist is None or dist > technician_radius:
            continue
        avg = (
            db.query(func.avg(Rating.score)).filter(Rating.technician_id == technician.id).scalar()
            or 0
        )
        result.append(
            {
                "id": technician.id,
                "name": technician.name,
                "phone": technician.phone,
                "status": technician.status,
                "availability_status": getattr(technician, "availability_status", None),
                "lat": technician.lat,
                "lng": technician.lng,
                "avg_rating": round(float(avg), 1),
                "distance_km": round(dist, 2) if dist is not None else None,
                "service_radius_km": round(technician_radius, 2),
                "work_start_time": technician.work_start_time,
                "work_end_time": technician.work_end_time,
                "work_days": sorted(parse_work_days(technician.work_days)),
                "acceptance_rate": round(float(technician.acceptance_rate or 0.0), 3),
                "completion_rate": round(float(technician.completion_rate or 0.0), 3),
                "priority_score": round(
                    compute_technician_priority_score(
                        distance_km=dist,
                        max_distance_km=technician_radius,
                        avg_rating=float(avg),
                        acceptance_rate=getattr(technician, "acceptance_rate", 0.0),
                        completion_rate=getattr(technician, "completion_rate", 0.0),
                    ),
                    6,
                ),
            }
        )

    result.sort(
        key=lambda row: (
            -row["priority_score"],
            row["distance_km"],
            -row["avg_rating"],
            -row["acceptance_rate"],
            -row["completion_rate"],
        )
    )
    return result[:limit]
