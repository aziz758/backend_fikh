from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, literal, or_
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models import Customer, Request, RequestService, Service, Technician, TechnicianService
from app.models.request_assignment import RequestAssignment
from app.schemas.admin import (
    BroadcastNotificationRequest,
    BroadcastNotificationResponse,
    TechnicianStatusUpdateRequest,
)
from app.schemas.common import SuccessResponse
from app.services.firebase_service import notify_user, sync_technician_realtime
from app.services.location_service import is_technician_location_fresh
from app.services.technician_schedule_service import parse_work_days

router = APIRouter()

VALID_TECHNICIAN_STATUSES = {"approved", "rejected", "pending_approval", "pending_documents"}


def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("type") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user


def _build_statistics(db: Session) -> dict:
    total_customers = db.query(func.count(Customer.id)).scalar() or 0
    total_technicians = db.query(func.count(Technician.id)).scalar() or 0
    pending_approval_count = (
        db.query(func.count(Technician.id))
        .filter(Technician.status == "pending_approval")
        .scalar()
        or 0
    )

    total_requests = db.query(func.count(Request.id)).scalar() or 0
    completed_requests = (
        db.query(func.count(Request.id)).filter(Request.status == "completed").scalar() or 0
    )
    cancelled_requests = (
        db.query(func.count(Request.id)).filter(Request.status == "cancelled").scalar() or 0
    )
    pending_requests = (
        db.query(func.count(Request.id)).filter(Request.status == "pending").scalar() or 0
    )
    assigned_requests = (
        db.query(func.count(Request.id))
        .filter(Request.status.in_(["assigned", "accepted"]))
        .scalar()
        or 0
    )
    avg_rating_platform = (
        db.query(func.avg(Request.customer_rating))
        .filter(Request.customer_rating.isnot(None))
        .scalar()
    )

    return {
        "total_customers": int(total_customers),
        "total_technicians": int(total_technicians),
        "pending_approval_count": int(pending_approval_count),
        "total_requests": int(total_requests),
        "completed_requests": int(completed_requests),
        "cancelled_requests": int(cancelled_requests),
        "pending_requests": int(pending_requests),
        "assigned_requests": int(assigned_requests),
        "avg_rating_platform": float(avg_rating_platform or 0.0),
    }


def _get_technician_services_map(db: Session, technician_ids: list[int]) -> dict[int, list[str]]:
    if not technician_ids:
        return {}

    rows = (
        db.query(TechnicianService.technician_id, Service.name)
        .join(Service, Service.id == TechnicianService.service_id)
        .filter(TechnicianService.technician_id.in_(technician_ids))
        .all()
    )
    services_map: dict[int, list[str]] = {}
    for technician_id, service_name in rows:
        services_map.setdefault(technician_id, []).append(service_name)
    return services_map


def _serialize_technician(tech: Technician, services_map: dict[int, list[str]]) -> dict:
    return {
        "id": tech.id,
        "name": tech.name or "",
        "phone": tech.phone or "",
        "status": tech.status or "",
        "availability_status": tech.availability_status or "",
        "avg_rating": float(tech.avg_rating or 0.0),
        "total_ratings": int(tech.total_ratings or 0),
        "acceptance_rate": float(tech.acceptance_rate or 0.0),
        "completion_rate": float(tech.completion_rate or 0.0),
        "profile_photo_url": tech.profile_photo_url or "",
        "id_card_photo_url": tech.id_card_photo_url or "",
        "service_radius_km": float(tech.service_radius_km) if tech.service_radius_km is not None else 0.0,
        "work_start_time": tech.work_start_time or "",
        "work_end_time": tech.work_end_time or "",
        "work_days": sorted(parse_work_days(tech.work_days)),
        "services": services_map.get(tech.id, []),
        "created_at": str(tech.created_at) if tech.created_at else "",
    }


def _set_technician_available_if_location_fresh(tech: Technician) -> None:
    tech.availability_status = "available" if is_technician_location_fresh(tech) else "offline"


def _get_request_services_map(db: Session, request_ids: list[int]) -> dict[int, list[str]]:
    if not request_ids:
        return {}

    rows = (
        db.query(
            RequestService.request_id,
            RequestService.service_type_name,
            Service.name,
        )
        .outerjoin(Service, Service.id == RequestService.service_id)
        .filter(RequestService.request_id.in_(request_ids))
        .all()
    )
    services_map: dict[int, list[str]] = {}
    for request_id, service_type_name, service_name in rows:
        resolved_name = service_type_name or service_name
        if resolved_name:
            services_map.setdefault(request_id, []).append(resolved_name)
    return services_map


def _get_request_latest_rejections_map(
    db: Session,
    request_ids: list[int],
) -> dict[int, dict[str, str]]:
    if not request_ids:
        return {}

    rows = (
        db.query(
            RequestAssignment.request_id,
            RequestAssignment.reject_reason,
            RequestAssignment.rejected_at,
        )
        .filter(
            RequestAssignment.request_id.in_(request_ids),
            RequestAssignment.status == "rejected",
            RequestAssignment.reject_reason.isnot(None),
        )
        .order_by(RequestAssignment.request_id.asc(), RequestAssignment.rejected_at.desc())
        .all()
    )
    latest_map: dict[int, dict[str, str]] = {}
    for request_id, reject_reason, rejected_at in rows:
        if request_id in latest_map:
            continue
        latest_map[request_id] = {
            "reason": reject_reason or "",
            "rejected_at": str(rejected_at) if rejected_at else "",
        }
    return latest_map


def _serialize_request(
    req: Request,
    services_map: dict[int, list[str]],
    latest_rejections_map: dict[int, dict[str, str]],
) -> dict:
    customer = req.customer
    technician = req.assigned_technician
    latest_rejection = latest_rejections_map.get(req.id, {})
    return {
        "id": req.id,
        "status": req.status or "",
        "note": req.note or "",
        "image_url": req.image_url or "",
        "address": req.address or "",
        "lat": float(req.lat) if req.lat is not None else 0.0,
        "lng": float(req.lng) if req.lng is not None else 0.0,
        "created_at": str(req.created_at) if req.created_at else "",
        "customer_id": req.customer_id,
        "customer_name": customer.name if customer else "",
        "customer_phone": customer.phone if customer else "",
        "technician_id": req.assigned_technician_id or 0,
        "technician_name": technician.name if technician else "",
        "technician_phone": technician.phone if technician else "",
        "services": services_map.get(req.id, []),
        "customer_rating": float(req.customer_rating) if req.customer_rating is not None else 0.0,
        "technician_report": req.technician_report or "",
        "latest_reject_reason": latest_rejection.get("reason", ""),
        "latest_rejected_at": latest_rejection.get("rejected_at", ""),
    }


def _serialize_rating(req: Request) -> dict:
    customer = req.customer
    technician = req.assigned_technician
    return {
        "request_id": req.id,
        "rating": float(req.customer_rating or 0.0),
        "comment": "",
        "customer_name": customer.name if customer else "",
        "customer_phone": customer.phone if customer else "",
        "technician_name": technician.name if technician else "",
        "technician_phone": technician.phone if technician else "",
        "created_at": str(req.created_at) if req.created_at else "",
    }


@router.get("/statistics")
def get_admin_statistics(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _build_statistics(db)


@router.get("/technicians")
def list_technicians_for_admin(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Technician)
    if status:
        query = query.filter(Technician.status == status)

    total = query.count()
    technicians = (
        query.order_by(Technician.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    services_map = _get_technician_services_map(db, [t.id for t in technicians])

    return {
        "results": [_serialize_technician(t, services_map) for t in technicians],
        "total": total,
        "page": page,
    }


@router.put("/technicians/{technician_id}/status", response_model=SuccessResponse)
def update_technician_status(
    technician_id: int,
    body: TechnicianStatusUpdateRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    new_status = body.status
    if new_status not in VALID_TECHNICIAN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    technician = db.query(Technician).filter(Technician.id == technician_id).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")

    technician.status = new_status
    if new_status == "approved":
        _set_technician_available_if_location_fresh(technician)
    elif new_status == "rejected":
        technician.availability_status = "offline"

    db.commit()
    sync_technician_realtime(technician)

    if new_status == "approved":
        notify_user(
            db=db,
            user_id=technician.id,
            user_type="technician",
            title="Your account has been approved",
            body="You can now receive requests",
            type="account_approved",
        )
    elif new_status == "rejected":
        notify_user(
            db=db,
            user_id=technician.id,
            user_type="technician",
            title="Your account was not approved",
            body="Please contact support to know the reason",
            type="account_rejected",
        )

    return {"success": True}


@router.get("/requests")
def list_requests_for_admin(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Request).options(
        joinedload(Request.customer),
        joinedload(Request.assigned_technician),
        joinedload(Request.request_services),
    )
    if status:
        query = query.filter(Request.status == status)

    total = query.count()
    requests_list = (
        query.order_by(Request.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    services_map = _get_request_services_map(db, [r.id for r in requests_list])
    latest_rejections_map = _get_request_latest_rejections_map(
        db,
        [r.id for r in requests_list],
    )

    return {
        "results": [
            _serialize_request(req, services_map, latest_rejections_map) for req in requests_list
        ],
        "total": total,
        "page": page,
    }


@router.get("/ratings")
def list_ratings_for_admin(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    rated_requests = (
        db.query(Request)
        .options(joinedload(Request.customer), joinedload(Request.assigned_technician))
        .filter(Request.customer_rating.isnot(None))
        .order_by(Request.created_at.desc())
        .all()
    )
    results = [_serialize_rating(req) for req in rated_requests]

    return {"results": results, "total": len(results)}


@router.post("/notifications/broadcast", response_model=BroadcastNotificationResponse)
def broadcast_notification(
    body: BroadcastNotificationRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    title = body.title.strip()
    message_body = body.body.strip()
    target = body.target
    raw_user_ids = body.user_ids

    if not title or not message_body:
        raise HTTPException(status_code=400, detail="title and body are required")
    sent_count = 0

    if target in {"all", "customers"}:
        customers = db.query(Customer).all()
        for customer in customers:
            try:
                notify_user(
                    db=db,
                    user_id=customer.id,
                    user_type="customer",
                    title=title,
                    body=message_body,
                    type="admin_broadcast",
                )
                sent_count += 1
            except Exception:
                continue

    if target == "all":
        technicians = db.query(Technician).all()
        for technician in technicians:
            try:
                notify_user(
                    db=db,
                    user_id=technician.id,
                    user_type="technician",
                    title=title,
                    body=message_body,
                    type="admin_broadcast",
                )
                sent_count += 1
            except Exception:
                continue

    if target == "technicians":
        technicians = db.query(Technician).filter(Technician.status == "approved").all()
        for technician in technicians:
            try:
                notify_user(
                    db=db,
                    user_id=technician.id,
                    user_type="technician",
                    title=title,
                    body=message_body,
                    type="admin_broadcast",
                )
                sent_count += 1
            except Exception:
                continue

    if target == "specific":
        user_ids: set[int] = set(raw_user_ids)

        customers = db.query(Customer).filter(Customer.id.in_(user_ids)).all()
        technicians = db.query(Technician).filter(Technician.id.in_(user_ids)).all()

        for customer in customers:
            try:
                notify_user(
                    db=db,
                    user_id=customer.id,
                    user_type="customer",
                    title=title,
                    body=message_body,
                    type="admin_broadcast",
                )
                sent_count += 1
            except Exception:
                continue

        for technician in technicians:
            try:
                notify_user(
                    db=db,
                    user_id=technician.id,
                    user_type="technician",
                    title=title,
                    body=message_body,
                    type="admin_broadcast",
                )
                sent_count += 1
            except Exception:
                continue

    return {"success": True, "sent_count": sent_count}


@router.get("/users")
def list_users_for_admin(
    user_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_type and user_type not in {"customer", "technician"}:
        raise HTTPException(status_code=400, detail="user_type must be customer or technician")

    search_term = f"%{search.strip()}%" if search and search.strip() else None

    customer_query = db.query(
        Customer.id.label("id"),
        Customer.name.label("name"),
        Customer.phone.label("phone"),
        literal("customer").label("user_type"),
        Customer.status.label("status"),
        Customer.created_at.label("created_at"),
    )
    if search_term:
        customer_query = customer_query.filter(
            or_(Customer.name.like(search_term), Customer.phone.like(search_term))
        )

    technician_query = db.query(
        Technician.id.label("id"),
        Technician.name.label("name"),
        Technician.phone.label("phone"),
        literal("technician").label("user_type"),
        Technician.status.label("status"),
        Technician.created_at.label("created_at"),
    )
    if search_term:
        technician_query = technician_query.filter(
            or_(Technician.name.like(search_term), Technician.phone.like(search_term))
        )

    if user_type == "customer":
        users_subquery = customer_query.subquery()
    elif user_type == "technician":
        users_subquery = technician_query.subquery()
    else:
        users_subquery = customer_query.union_all(technician_query).subquery()

    total = db.query(func.count()).select_from(users_subquery).scalar() or 0
    rows = (
        db.query(
            users_subquery.c.id,
            users_subquery.c.name,
            users_subquery.c.phone,
            users_subquery.c.user_type,
            users_subquery.c.status,
            users_subquery.c.created_at,
        )
        .order_by(users_subquery.c.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    results = [
        {
            "id": row.id,
            "name": row.name or "",
            "phone": row.phone or "",
            "user_type": row.user_type,
            "status": row.status or "",
            "created_at": str(row.created_at) if row.created_at else "",
        }
        for row in rows
    ]
    return {"results": results, "total": int(total), "page": page}


@router.delete("/users/{user_id}")
def soft_delete_user(
    user_id: int,
    user_type: str = Query(...),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_type not in {"customer", "technician"}:
        raise HTTPException(status_code=400, detail="user_type must be customer or technician")

    if user_type == "customer":
        user = db.query(Customer).filter(Customer.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Customer not found")
        user.status = "inactive"
    else:
        user = db.query(Technician).filter(Technician.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Technician not found")
        user.status = "inactive"
        user.availability_status = "offline"

    db.commit()
    return {"success": True}


@router.get("/dashboard")
def get_admin_dashboard(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    statistics = _build_statistics(db)

    recent_requests_query = (
        db.query(Request)
        .options(
            joinedload(Request.customer),
            joinedload(Request.assigned_technician),
            joinedload(Request.request_services),
        )
        .order_by(Request.created_at.desc())
        .limit(5)
        .all()
    )
    recent_request_services_map = _get_request_services_map(
        db,
        [req.id for req in recent_requests_query],
    )
    recent_request_rejections_map = _get_request_latest_rejections_map(
        db,
        [req.id for req in recent_requests_query],
    )
    recent_requests = [
        _serialize_request(req, recent_request_services_map, recent_request_rejections_map)
        for req in recent_requests_query
    ]

    pending_technicians_query = (
        db.query(Technician)
        .filter(Technician.status == "pending_approval")
        .order_by(Technician.created_at.desc())
        .all()
    )
    pending_services_map = _get_technician_services_map(
        db,
        [tech.id for tech in pending_technicians_query],
    )
    pending_technicians = [
        _serialize_technician(tech, pending_services_map)
        for tech in pending_technicians_query
    ]

    recent_ratings_query = (
        db.query(Request)
        .options(joinedload(Request.customer), joinedload(Request.assigned_technician))
        .filter(Request.customer_rating.isnot(None))
        .order_by(Request.created_at.desc())
        .limit(5)
        .all()
    )
    recent_ratings = [_serialize_rating(req) for req in recent_ratings_query]

    return {
        "statistics": statistics,
        "recent_requests": recent_requests,
        "pending_technicians": pending_technicians,
        "recent_ratings": recent_ratings,
    }


