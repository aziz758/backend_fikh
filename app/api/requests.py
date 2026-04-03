from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, require_customer, require_technician
from app.database import SessionLocal, get_db
from app.models import Rating, Request, RequestService, Technician
from app.models.request_assignment import RequestAssignment
from app.schemas.request_schema import RequestCreate, RequestResponse
from app.services.assignment_service import find_best_technician, schedule_assignment_timeout

router = APIRouter(prefix="/requests", tags=["requests"])


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
    new_request = Request(
        customer_id=customer_id,
        note=body.note,
        image_url=body.image_url,
        lat=body.lat,
        lng=body.lng,
        address=body.address,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    for i, sid in enumerate(body.service_ids):
        sname = None
        if body.service_type_names and i < len(body.service_type_names):
            sname = body.service_type_names[i]
        rs = RequestService(
            request_id=new_request.id,
            service_id=sid,
            service_type_name=sname,
        )
        db.add(rs)
    db.commit()

    service_id = body.service_ids[0] if body.service_ids else None
    best_tech = (
        find_best_technician(db, service_id, body.lat, body.lng, excluded_ids=[])
        if service_id is not None
        else None
    )

    if best_tech:
        timeout_at = datetime.utcnow() + timedelta(minutes=5)
        assignment = RequestAssignment(
            request_id=new_request.id,
            technician_id=best_tech.id,
            status="pending",
            timeout_at=timeout_at,
        )
        db.add(assignment)
        new_request.assigned_technician_id = best_tech.id
        new_request.status = "assigned"
        db.commit()
        db.refresh(assignment)

        from app.services.firebase_service import notify_user

        notify_user(
            db=db,
            user_id=best_tech.id,
            user_type="technician",
            title="طلب خدمة جديد",
            body="لديك طلب خدمة جديد، يرجى الرد خلال 5 دقائق",
            type="new_request",
            data={"request_id": str(new_request.id)},
        )

        schedule_assignment_timeout(new_request.id, assignment.id, SessionLocal)
    else:
        new_request.status = "pending"
        db.commit()

    db.refresh(new_request)
    return _serialize_request(db, new_request)


@router.post("/{request_id}/accept", response_model=RequestResponse)
def accept_request(
    request_id: int,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    current_tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if not current_tech:
        raise HTTPException(status_code=404, detail="الفني غير موجود")

    if request.assigned_technician_id is None:
        request.assigned_technician_id = technician_id
    elif request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="هذا الطلب غير مسند لك")

    request.status = "accepted"

    assignment = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.request_id == request_id,
            RequestAssignment.technician_id == current_tech.id,
            RequestAssignment.status == "pending",
        )
        .first()
    )
    if assignment:
        assignment.status = "accepted"

    current_tech.availability_status = "busy"

    total = db.query(RequestAssignment).filter(RequestAssignment.technician_id == current_tech.id).count()
    accepted = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.technician_id == current_tech.id,
            RequestAssignment.status == "accepted",
        )
        .count()
    )
    current_tech.acceptance_rate = accepted / total if total > 0 else 0
    db.commit()

    from app.services.firebase_service import notify_user

    notify_user(
        db=db,
        user_id=request.customer_id,
        user_type="customer",
        title="تم قبول طلبك",
        body="الفني في الطريق إليك",
        type="request_accepted",
        data={"request_id": str(request_id)},
    )

    db.refresh(request)
    return _serialize_request(db, request)


@router.post("/{request_id}/complete", response_model=RequestResponse)
def complete_request(
    request_id: int,
    body: dict,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="هذا الطلب غير مسند لك")

    report = (body or {}).get("report")
    if not report or not str(report).strip():
        raise HTTPException(status_code=400, detail="التقرير مطلوب")

    request.technician_report = str(report).strip()
    request.status = "completed"

    current_tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if current_tech:
        current_tech.availability_status = "available"

        total_accepted = (
            db.query(RequestAssignment)
            .filter(
                RequestAssignment.technician_id == current_tech.id,
                RequestAssignment.status == "accepted",
            )
            .count()
        )
        total_completed = (
            db.query(Request)
            .filter(
                Request.assigned_technician_id == current_tech.id,
                Request.status == "completed",
            )
            .count()
        )
        current_tech.completion_rate = total_completed / total_accepted if total_accepted > 0 else 0

    db.commit()

    from app.services.firebase_service import notify_user

    notify_user(
        db=db,
        user_id=request.customer_id,
        user_type="customer",
        title="تم إنجاز طلبك",
        body="قام الفني بإنجاز طلبك، يرجى التقييم",
        type="request_completed",
        data={"request_id": str(request_id)},
    )

    db.refresh(request)
    return _serialize_request(db, request)


@router.post("/{request_id}/rate", response_model=RequestResponse)
def rate_request(
    request_id: int,
    body: dict,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
):
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if request.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="غير مصرح")
    if request.status != "completed":
        raise HTTPException(status_code=400, detail="لا يمكن التقييم قبل إنجاز الطلب")
    if request.customer_rating is not None:
        return _serialize_request(db, request)

    rating = (body or {}).get("rating")
    try:
        rating_value = float(rating)
    except Exception:
        raise HTTPException(status_code=400, detail="قيمة التقييم غير صحيحة")
    if rating_value < 1 or rating_value > 5:
        raise HTTPException(status_code=400, detail="التقييم يجب أن يكون بين 1 و 5")

    request.customer_rating = rating_value

    tech = None
    if request.assigned_technician_id is not None:
        db.add(
            Rating(
                customer_id=customer_id,
                technician_id=request.assigned_technician_id,
                score=rating_value,
                comment=None,
            )
        )

        tech = db.query(Technician).filter(Technician.id == request.assigned_technician_id).first()
        if tech:
            current_total = tech.total_ratings or 0
            current_avg = tech.avg_rating or 0.0
            tech.avg_rating = ((current_avg * current_total) + rating_value) / (current_total + 1)
            tech.total_ratings = current_total + 1

    db.commit()

    if tech:
        from app.services.firebase_service import notify_user

        notify_user(
            db=db,
            user_id=tech.id,
            user_type="technician",
            title="تقييم جديد",
            body=f"حصلت على تقييم {rating_value} من 5",
            type="request_rated",
            data={"request_id": str(request_id)},
        )

    db.refresh(request)
    return _serialize_request(db, request)
