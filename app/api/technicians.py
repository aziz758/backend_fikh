from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models import Technician, TechnicianService, Rating

router = APIRouter(prefix="/technicians", tags=["technicians"])


def haversine_distance(lat1, lng1, lat2, lng2):
    """المسافة بالكيلومتر تقريباً"""
    import math
    R = 6371
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


@router.get("/nearby")
def get_nearby_technicians(
    service_id: int = Query(...),
    customer_lat: float = Query(...),
    customer_lng: float = Query(...),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """جلب أقرب الفنيين وأعلى تقييماً للخدمة المحددة"""
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
            or_(Technician.status == "approved", Technician.status == "available"),
            or_(Technician.availability_status == "available", Technician.availability_status.is_(None)),
        )
        .all()
    )
    result = []
    for t in techs:
        if t.lat is None or t.lng is None:
            continue
        dist = haversine_distance(customer_lat, customer_lng, t.lat, t.lng)
        avg = db.query(func.avg(Rating.score)).filter(Rating.technician_id == t.id).scalar() or 0
        result.append({
            "id": t.id,
            "name": t.name,
            "phone": t.phone,
            "status": t.status,
            "availability_status": getattr(t, "availability_status", None),
            "lat": t.lat,
            "lng": t.lng,
            "avg_rating": round(float(avg), 1),
            "distance_km": round(dist, 2),
        })
    result.sort(key=lambda x: (-x["avg_rating"], x["distance_km"]))
    return result[:limit]
