from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Rating, Request as RequestModel, Service, Technician, TechnicianService, TechnicianServiceArea
from app.services.location_validation_service import validate_area_selection
from app.services.location_service import location_cutoff_utc, mark_stale_available_technicians_offline
from app.services.technician_priority_service import compute_technician_priority_score
from app.services.technician_schedule_service import (
    is_technician_within_working_hours,
    parse_work_days,
    resolve_service_radius_km,
)
from app.services.upload_service import public_upload_url

router = APIRouter(prefix="/technicians", tags=["technicians"])
TECHNICIAN_ACTIVE_REQUEST_STATUSES = ("accepted",)
TOP_TECHNICIAN_BAYESIAN_MIN_RATINGS = 5
TOP_TECHNICIAN_BAYESIAN_BASELINE = 4.0


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


def _weighted_rating(avg_rating: float, total_ratings: int) -> float:
    if total_ratings <= 0:
        return 0.0
    return (
        (avg_rating * total_ratings)
        + (TOP_TECHNICIAN_BAYESIAN_BASELINE * TOP_TECHNICIAN_BAYESIAN_MIN_RATINGS)
    ) / (total_ratings + TOP_TECHNICIAN_BAYESIAN_MIN_RATINGS)


def _rating_stats(
    db: Session,
    technician_id: int,
    *,
    governorate_id: int | None = None,
    district_id: int | None = None,
) -> tuple[float, int, int]:
    query = db.query(Rating).filter(Rating.technician_id == technician_id)
    if governorate_id is not None:
        query = query.join(RequestModel, Rating.request_id == RequestModel.id).filter(
            RequestModel.governorate_id == governorate_id,
        )
        if district_id is not None:
            query = query.filter(RequestModel.district_id == district_id)

    avg = query.with_entities(func.avg(Rating.score)).scalar() or 0.0
    total = query.with_entities(func.count(Rating.id)).scalar() or 0
    positive_comments = (
        query.filter(
            Rating.score >= 4,
            Rating.comment.isnot(None),
            func.length(func.trim(Rating.comment)) > 0,
        )
        .with_entities(func.count(Rating.id))
        .scalar()
        or 0
    )
    return round(float(avg or 0.0), 1), int(total or 0), int(positive_comments or 0)


def _positive_comments(
    db: Session,
    technician_id: int,
    *,
    governorate_id: int | None = None,
    district_id: int | None = None,
    limit: int = 3,
) -> list[dict]:
    query = db.query(Rating).filter(
        Rating.technician_id == technician_id,
        Rating.score >= 4,
        Rating.comment.isnot(None),
        func.length(func.trim(Rating.comment)) > 0,
    )
    if governorate_id is not None:
        query = query.join(RequestModel, Rating.request_id == RequestModel.id).filter(
            RequestModel.governorate_id == governorate_id,
        )
        if district_id is not None:
            query = query.filter(RequestModel.district_id == district_id)

    ratings = query.order_by(Rating.created_at.desc(), Rating.id.desc()).limit(limit).all()
    return [
        {
            "id": rating.id,
            "request_id": rating.request_id,
            "score": round(float(rating.score or 0.0), 1),
            "comment": str(rating.comment or "").strip(),
            "created_at": rating.created_at,
        }
        for rating in ratings
    ]


def _services_by_technician(
    db: Session,
    technician_ids: list[int],
) -> dict[int, list[dict]]:
    if not technician_ids:
        return {}
    rows = (
        db.query(TechnicianService.technician_id, Service.id, Service.name)
        .join(Service, Service.id == TechnicianService.service_id)
        .filter(TechnicianService.technician_id.in_(technician_ids))
        .order_by(TechnicianService.technician_id.asc(), Service.id.asc())
        .all()
    )
    result: dict[int, list[dict]] = {}
    for technician_id, service_id, service_name in rows:
        result.setdefault(technician_id, []).append(
            {
                "id": service_id,
                "name": service_name,
            }
        )
    return result


def _service_area_match_rank(
    technician: Technician,
    service_areas: list[TechnicianServiceArea],
    *,
    governorate_id: int | None,
    district_id: int | None,
) -> tuple[int, str]:
    if governorate_id is None:
        return 0, "not_filtered"

    if district_id is not None:
        if technician.governorate_id == governorate_id and technician.district_id == district_id:
            return 3, "primary_district"
        if any(
            area.governorate_id == governorate_id and area.district_id == district_id
            for area in service_areas
        ):
            return 3, "service_district"
        if any(
            area.governorate_id == governorate_id and area.district_id is None
            for area in service_areas
        ):
            return 2, "service_governorate"
        if technician.governorate_id == governorate_id and technician.district_id is None:
            return 2, "primary_governorate"
        return 0, "no_area_match"

    if technician.governorate_id == governorate_id:
        return 2, "primary_governorate"
    if any(area.governorate_id == governorate_id for area in service_areas):
        return 2, "service_governorate"
    return 0, "no_area_match"


@router.get("/top")
def get_top_technicians(
    service_id: int = Query(..., gt=0),
    governorate_id: int | None = Query(default=None, gt=0),
    district_id: int | None = Query(default=None, gt=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Browse approved technicians by service and area reputation."""
    validate_area_selection(db, governorate_id=governorate_id, district_id=district_id)

    technicians = (
        db.query(Technician)
        .join(TechnicianService, TechnicianService.technician_id == Technician.id)
        .filter(
            TechnicianService.service_id == service_id,
            Technician.status == "approved",
        )
        .distinct()
        .all()
    )
    technician_ids = [tech.id for tech in technicians]
    service_area_rows = (
        db.query(TechnicianServiceArea)
        .filter(TechnicianServiceArea.technician_id.in_(technician_ids))
        .all()
        if technicians
        else []
    )
    services_by_technician = _services_by_technician(db, technician_ids)
    service_areas_by_technician: dict[int, list[TechnicianServiceArea]] = {}
    for area in service_area_rows:
        service_areas_by_technician.setdefault(area.technician_id, []).append(area)

    results = []
    for technician in technicians:
        area_rank, area_match = _service_area_match_rank(
            technician,
            service_areas_by_technician.get(technician.id, []),
            governorate_id=governorate_id,
            district_id=district_id,
        )
        if governorate_id is not None and area_rank == 0:
            continue

        global_avg, global_total, global_positive_comments = _rating_stats(db, technician.id)
        if governorate_id is not None:
            area_avg, area_total, area_positive_comments = _rating_stats(
                db,
                technician.id,
                governorate_id=governorate_id,
                district_id=district_id,
            )
        else:
            area_avg, area_total, area_positive_comments = global_avg, global_total, global_positive_comments

        ranking_avg = area_avg if area_total > 0 else global_avg
        ranking_total = area_total if area_total > 0 else global_total
        ranking_comments = area_positive_comments if area_total > 0 else global_positive_comments
        comments_governorate_id = governorate_id if governorate_id is not None and area_total > 0 else None
        comments_district_id = district_id if comments_governorate_id is not None else None
        positive_comments = _positive_comments(
            db,
            technician.id,
            governorate_id=comments_governorate_id,
            district_id=comments_district_id,
        )
        reputation_score = _weighted_rating(ranking_avg, ranking_total)
        ranking_score = (
            (area_rank * 100.0)
            + (reputation_score * 10.0)
            + (min(ranking_total, 50) * 0.08)
            + (min(ranking_comments, 50) * 0.05)
            + (float(technician.completion_rate or 0.0) * 2.0)
            + (float(technician.acceptance_rate or 0.0) * 1.0)
        )

        results.append(
            {
                "id": technician.id,
                "name": technician.name,
                "phone": technician.phone,
                "status": technician.status,
                "availability_status": technician.availability_status,
                "profile_photo_url": public_upload_url(technician.profile_photo_url),
                "services": services_by_technician.get(technician.id, []),
                "governorate_id": technician.governorate_id,
                "governorate_name": technician.governorate.name_ar if technician.governorate else None,
                "district_id": technician.district_id,
                "district_name": technician.district.name_ar if technician.district else None,
                "address_details": technician.address_details,
                "avg_rating": global_avg,
                "total_ratings": global_total,
                "area_avg_rating": area_avg,
                "area_total_ratings": area_total,
                "positive_comment_count": ranking_comments,
                "positive_comments_scope": "area" if comments_governorate_id is not None else "global",
                "positive_comments": positive_comments,
                "area_match": area_match,
                "acceptance_rate": round(float(technician.acceptance_rate or 0.0), 3),
                "completion_rate": round(float(technician.completion_rate or 0.0), 3),
                "ranking_score": round(ranking_score, 6),
            }
        )

    results.sort(
        key=lambda row: (
            -row["ranking_score"],
            -row["area_total_ratings"],
            -row["avg_rating"],
            -row["total_ratings"],
            row["name"],
        )
    )
    return {"results": results[:limit], "total": len(results), "limit": limit}


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
                "profile_photo_url": public_upload_url(technician.profile_photo_url),
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
