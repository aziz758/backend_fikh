from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.schemas.request_schema import RequestCreate, RequestResponse
from app.models import Request, RequestService
from app.api.dependencies import require_customer, require_technician, get_current_user_id
from app.models import Technician, TechnicianService, Rating

router = APIRouter(prefix="/requests", tags=["requests"])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math

    R = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _avg_rating(db: Session, technician_id: int) -> float:
    avg = db.query(func.avg(Rating.score)).filter(Rating.technician_id == technician_id).scalar()
    return round(float(avg or 0.0), 1)


def _serialize_request(db: Session, req: Request) -> dict:
    service_ids = [rs.service_id for rs in (req.request_services or [])]
    service_names = [rs.service_type_name for rs in (req.request_services or []) if rs.service_type_name]

    tech = req.assigned_technician
    tech_rating = _avg_rating(db, tech.id) if tech else None

    return {
        "id": req.id,
        "customer_id": req.customer_id,
        "note": req.note,
        "image_url": req.image_url,
        "status": req.status,
        "created_at": req.created_at,
        "service_ids": service_ids,
        "service_type_names": service_names,
        "lat": getattr(req, "lat", None),
        "lng": getattr(req, "lng", None),
        "address": getattr(req, "address", None),
        "assigned_technician_id": getattr(req, "assigned_technician_id", None),
        "assigned_technician_name": tech.name if tech else None,
        "assigned_technician_rating": tech_rating,
        "technician_report": getattr(req, "technician_report", None),
        "customer_rating": getattr(req, "customer_rating", None),
    }


def _choose_technician_for_request(
    db: Session,
    service_id: int,
    customer_lat: float | None,
    customer_lng: float | None,
) -> Technician | None:
    techs = (
        db.query(Technician)
        .join(TechnicianService, TechnicianService.technician_id == Technician.id)
        .filter(
            TechnicianService.service_id == service_id,
            Technician.status == "available",
        )
        .all()
    )
    if not techs:
        return None

    scored: list[tuple[float, float, Technician]] = []
    for t in techs:
        avg = _avg_rating(db, t.id)
        dist = 0.0
        if customer_lat is not None and customer_lng is not None and t.lat is not None and t.lng is not None:
            dist = _haversine_km(customer_lat, customer_lng, t.lat, t.lng)
        scored.append((avg, dist, t))

    # الأعلى تقييماً ثم الأقرب
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]


@router.get("/", response_model=list[RequestResponse])
def list_my_requests(
    creds=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user_id, user_type = creds
    q = db.query(Request).order_by(Request.created_at.desc())
    if user_type == "customer":
        q = q.filter(Request.customer_id == user_id)
    elif user_type == "technician":
        q = q.filter(Request.assigned_technician_id == user_id)
    else:
        raise HTTPException(status_code=403, detail="نوع مستخدم غير مدعوم")

    reqs = q.all()
    return [_serialize_request(db, r) for r in reqs]


@router.post("/", response_model=RequestResponse)
def create_request(
    body: RequestCreate,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
):
    req = Request(
        customer_id=customer_id,
        note=body.note,
        image_url=body.image_url,
        lat=body.lat,
        lng=body.lng,
        address=body.address,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    for i, sid in enumerate(body.service_ids):
        sname = None
        if body.service_type_names and i < len(body.service_type_names):
            sname = body.service_type_names[i]
        rs = RequestService(
            request_id=req.id,
            service_id=sid,
            service_type_name=sname,
        )
        db.add(rs)
    db.commit()

    # إسناد تلقائي للفني الأعلى تقييماً (ثم الأقرب) لخدمة الطلب الأولى
    first_service_id = body.service_ids[0] if body.service_ids else None
    if first_service_id is not None:
        chosen = _choose_technician_for_request(db, first_service_id, body.lat, body.lng)
        if chosen is not None:
            req.assigned_technician_id = chosen.id
            req.status = "assigned"
        else:
            req.status = "pending"
    else:
        req.status = "pending"
    db.commit()
    db.refresh(req)
    return _serialize_request(db, req)


@router.post("/{request_id}/accept", response_model=RequestResponse)
def accept_request(
    request_id: int,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    if req.assigned_technician_id is None:
        req.assigned_technician_id = technician_id
    elif req.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="هذا الطلب غير مسند لك")

    req.status = "accepted"
    db.commit()
    db.refresh(req)
    return _serialize_request(db, req)


@router.post("/{request_id}/complete", response_model=RequestResponse)
def complete_request(
    request_id: int,
    body: dict,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if req.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="هذا الطلب غير مسند لك")

    report = (body or {}).get("report")
    if not report or not str(report).strip():
        raise HTTPException(status_code=400, detail="التقرير مطلوب")

    req.technician_report = str(report).strip()
    req.status = "completed"
    db.commit()
    db.refresh(req)
    return _serialize_request(db, req)


@router.post("/{request_id}/rate", response_model=RequestResponse)
def rate_request(
    request_id: int,
    body: dict,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
):
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if req.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="غير مصرح")
    if req.status != "completed":
        raise HTTPException(status_code=400, detail="لا يمكن التقييم قبل إنجاز الطلب")
    if req.customer_rating is not None:
        # لا نسمح بإعادة التقييم لنفس الطلب في النسخة الحالية
        return _serialize_request(db, req)

    rating = (body or {}).get("rating")
    try:
        rating_value = float(rating)
    except Exception:
        raise HTTPException(status_code=400, detail="قيمة التقييم غير صحيحة")
    if rating_value < 1 or rating_value > 5:
        raise HTTPException(status_code=400, detail="التقييم يجب أن يكون بين 1 و 5")

    req.customer_rating = rating_value

    # نضيفه أيضاً لجدول ratings لحساب متوسط تقييم الفني
    if req.assigned_technician_id is not None:
        db.add(
            Rating(
                customer_id=customer_id,
                technician_id=req.assigned_technician_id,
                score=rating_value,
                comment=None,
            )
        )

    db.commit()
    db.refresh(req)
    return _serialize_request(db, req)
