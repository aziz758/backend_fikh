from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
    get_current_user_id,
    require_customer,
    require_technician,
)
from app.database import SessionLocal, get_db
from app.models import Rating, Request as RequestModel, RequestService, Service, Technician
from app.models.request_assignment import RequestAssignment
from app.schemas.request_schema import (
    RequestCancel,
    RequestComplete,
    RequestCreate,
    RequestRate,
    RequestReject,
    RequestListResponse,
    RequestResponse,
)
from app.services.assignment_service import find_best_technician, schedule_assignment_timeout
from app.services.location_service import (
    is_technician_location_fresh,
    sync_technician_availability_with_location,
)
from app.services.request_state_machine import (
    InvalidRequestStatusTransition,
    apply_request_status_transition,
)
from app.services.upload_service import save_validated_image_upload

router = APIRouter(prefix="/requests", tags=["requests"])
upload_router = APIRouter()
TECHNICIAN_ACTIVE_REQUEST_STATUSES = ("accepted",)
TECHNICIAN_VISIBLE_WHILE_BREAK_STATUSES = TECHNICIAN_ACTIVE_REQUEST_STATUSES + ("completed",)
REQUEST_FILTER_STATUSES = {"pending", "assigned", "accepted", "completed", "cancelled"}


@upload_router.post("/request-image/")
async def upload_request_image(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()

    # Accept both "file" and "image" field names
    file = form.get("file") or form.get("image")

    if not file:
        raise HTTPException(
            status_code=400,
            detail="No image provided. Use field name 'file' or 'image'",
        )

    saved = save_validated_image_upload(file, "uploads", public_prefix="/uploads")
    return {"image_url": saved.url, "url": saved.url}


@upload_router.post("/profile-image/")
async def upload_profile_image(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    file = form.get("file")

    if not file:
        raise HTTPException(
            status_code=400,
            detail="No image provided. Use field name 'file'",
        )

    saved = save_validated_image_upload(file, "uploads", public_prefix="/uploads")
    return {"image_url": saved.url}


def _avg_rating(db: Session, technician_id: int) -> float:
    avg = db.query(func.avg(Rating.score)).filter(Rating.technician_id == technician_id).scalar()
    return round(float(avg or 0.0), 1)


def _update_technician_acceptance_rate(db: Session, technician_id: int) -> None:
    total = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.technician_id == technician_id,
            RequestAssignment.status != "cancelled",
        )
        .count()
    )
    accepted = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.technician_id == technician_id,
            RequestAssignment.status == "accepted",
        )
        .count()
    )
    tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if tech:
        tech.acceptance_rate = accepted / total if total > 0 else 0


def _ensure_technician_has_fresh_location(db: Session, tech: Technician) -> None:
    if is_technician_location_fresh(tech):
        return
    before = tech.availability_status
    sync_technician_availability_with_location(tech)
    if tech.availability_status != before:
        db.commit()
    raise HTTPException(
        status_code=409,
        detail=(
            "Live location is required before accepting requests. "
            "Please update your location."
        ),
    )


def _set_technician_available_if_location_fresh(tech: Technician) -> None:
    tech.availability_status = "available" if is_technician_location_fresh(tech) else "offline"


def _get_active_request_for_technician(
    db: Session,
    technician_id: int,
    *,
    exclude_request_id: int | None = None,
    for_update: bool = False,
) -> RequestModel | None:
    query = db.query(RequestModel).filter(
        RequestModel.assigned_technician_id == technician_id,
        RequestModel.status.in_(TECHNICIAN_ACTIVE_REQUEST_STATUSES),
    )
    if exclude_request_id is not None:
        query = query.filter(RequestModel.id != exclude_request_id)
    if for_update:
        query = query.with_for_update()
    return query.order_by(RequestModel.created_at.desc()).first()


def _build_navigation_links(lat: float | None, lng: float | None) -> dict[str, str | None]:
    if lat is None or lng is None:
        return {
            "google_maps_directions_url": None,
            "apple_maps_directions_url": None,
            "google_navigation_uri": None,
            "geo_navigation_uri": None,
        }

    coord = f"{lat:.6f},{lng:.6f}"
    return {
        "google_maps_directions_url": f"https://www.google.com/maps/dir/?api=1&destination={coord}",
        "apple_maps_directions_url": f"http://maps.apple.com/?daddr={coord}&dirflg=d",
        "google_navigation_uri": f"google.navigation:q={coord}",
        "geo_navigation_uri": f"geo:{coord}?q={coord}",
    }


def build_request_response(request: RequestModel, db: Session) -> dict:
    request_services = (
        db.query(RequestService, Service.name)
        .outerjoin(Service, Service.id == RequestService.service_id)
        .filter(RequestService.request_id == request.id)
        .all()
    )

    service_ids = [rs.service_id for rs, _ in request_services]
    service_names = []
    for rs, service_name in request_services:
        resolved_name = rs.service_type_name or service_name
        if resolved_name:
            service_names.append(resolved_name)

    technician_name = None
    technician_rating = None
    technician_avatar = None
    if request.assigned_technician_id:
        tech = db.query(Technician).filter(Technician.id == request.assigned_technician_id).first()
        if tech:
            technician_name = tech.name
            technician_rating = tech.avg_rating
            technician_avatar = tech.profile_photo_url

    latest_rejection = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.request_id == request.id,
            RequestAssignment.status == "rejected",
            RequestAssignment.reject_reason.isnot(None),
        )
        .order_by(RequestAssignment.rejected_at.desc(), RequestAssignment.id.desc())
        .first()
    )
    latest_reject_reason = latest_rejection.reject_reason if latest_rejection else None
    latest_rejected_at = latest_rejection.rejected_at if latest_rejection else None
    navigation_links = _build_navigation_links(request.lat, request.lng)

    return {
        "id": request.id,
        "status": request.status,
        "note": request.note,
        "image_url": request.image_url,
        "lat": request.lat,
        "lng": request.lng,
        "address": request.address,
        "created_at": str(request.created_at) if request.created_at else None,
        "customer_id": request.customer_id,
        "assigned_technician_id": request.assigned_technician_id,
        "assigned_technician_name": technician_name,
        "assigned_technician_rating": technician_rating,
        "assigned_technician_avatar": technician_avatar,
        "service_id": service_ids[0] if service_ids else None,
        "service_ids": service_ids,
        "service_type_names": service_names,
        "technician_report": request.technician_report,
        "customer_rating": request.customer_rating,
        "rating_comment": getattr(request, "rating_comment", None),
        "assigned_at": str(request.assigned_at) if getattr(request, "assigned_at", None) else None,
        "accepted_at": str(request.accepted_at) if getattr(request, "accepted_at", None) else None,
        "completed_at": str(request.completed_at) if getattr(request, "completed_at", None) else None,
        "latest_reject_reason": latest_reject_reason,
        "latest_rejected_at": str(latest_rejected_at) if latest_rejected_at else None,
        "google_maps_directions_url": navigation_links["google_maps_directions_url"],
        "apple_maps_directions_url": navigation_links["apple_maps_directions_url"],
        "google_navigation_uri": navigation_links["google_navigation_uri"],
        "geo_navigation_uri": navigation_links["geo_navigation_uri"],
    }


def _sync_technician_realtime_state(tech: Technician | None) -> None:
    if not tech:
        return
    from app.services.firebase_service import sync_technician_realtime

    sync_technician_realtime(tech)


def _sync_request_realtime_state(request: RequestModel, db: Session) -> None:
    from app.services.firebase_service import (
        clear_request_tracking_realtime,
        sync_request_realtime,
        sync_request_tracking_realtime,
    )

    sync_request_realtime(request)

    assigned_tech = None
    if request.assigned_technician_id:
        assigned_tech = db.query(Technician).filter(Technician.id == request.assigned_technician_id).first()

    if assigned_tech and request.status in ("assigned", "accepted"):
        sync_request_tracking_realtime(request, assigned_tech)
        return

    if request.status in ("completed", "cancelled") or request.assigned_technician_id is None:
        clear_request_tracking_realtime(request.id, status=request.status)


def _reject_legacy_wrapped_query_param(raw_request: Request) -> None:
    if "wrapped" in raw_request.query_params:
        raise HTTPException(
            status_code=400,
            detail=(
                "Query parameter 'wrapped' is no longer supported. "
                "Use the canonical response shape."
            ),
        )


@router.get("/", response_model=RequestListResponse)
def list_my_requests(
    raw_request: Request,
    creds=Depends(get_current_user_id),
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    user_id, user_type = creds
    _reject_legacy_wrapped_query_param(raw_request)

    q = db.query(RequestModel).order_by(RequestModel.created_at.desc())

    if status is not None and status not in REQUEST_FILTER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    if user_type == "customer":
        q = q.filter(RequestModel.customer_id == user_id)
    elif user_type == "technician":
        current_tech = db.query(Technician).filter(Technician.id == user_id).first()
        if not current_tech:
            raise HTTPException(status_code=404, detail="Technician not found")
        q = q.filter(RequestModel.assigned_technician_id == user_id)
        before = current_tech.availability_status
        sync_technician_availability_with_location(current_tech)
        if current_tech.availability_status != before:
            db.commit()
        if current_tech.availability_status == "on_break":
            # During break, hide incoming offers and show only active/history work.
            q = q.filter(RequestModel.status.in_(TECHNICIAN_VISIBLE_WHILE_BREAK_STATUSES))
        elif not is_technician_location_fresh(current_tech):
            # Without fresh location, technician can only see currently active jobs
            # and won't receive/view new assignments.
            q = q.filter(RequestModel.status.in_(TECHNICIAN_ACTIVE_REQUEST_STATUSES))
    else:
        raise HTTPException(status_code=403, detail="Unsupported user type")

    if status is not None:
        q = q.filter(RequestModel.status == status)

    total = q.count()
    reqs = q.offset((page - 1) * limit).limit(limit).all()
    results = [build_request_response(r, db) for r in reqs]
    payload = {
        "results": results,
        "total": total,
        "page": page,
        "limit": limit,
    }
    return payload


@router.get("/{request_id}", response_model=RequestResponse)
@router.get("/{request_id}/", response_model=RequestResponse, include_in_schema=False)
def get_request_details(
    request_id: int,
    raw_request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _reject_legacy_wrapped_query_param(raw_request)

    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    user_type = current_user.get("type")
    user_id = current_user.get("id")

    if user_type == "customer":
        if request.customer_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
    elif user_type == "technician":
        assignment_exists = (
            db.query(RequestAssignment.id)
            .filter(
                RequestAssignment.request_id == request_id,
                RequestAssignment.technician_id == user_id,
            )
            .first()
        )
        if request.assigned_technician_id != user_id and not assignment_exists:
            raise HTTPException(status_code=403, detail="Unauthorized")
    elif user_type != "admin":
        raise HTTPException(status_code=403, detail="Unsupported user type")

    payload = build_request_response(request, db)
    return payload


@router.post("/", response_model=RequestResponse)
def create_request(
    body: RequestCreate,
    raw_request: Request,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
):
    _reject_legacy_wrapped_query_param(raw_request)
    request_data = body

    new_request = RequestModel(
        customer_id=customer_id,
        note=request_data.note,
        image_url=request_data.image_url,
        lat=request_data.lat,
        lng=request_data.lng,
        address=request_data.address,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    for i, sid in enumerate(request_data.service_ids):
        sname = None
        if request_data.service_type_names and i < len(request_data.service_type_names):
            sname = request_data.service_type_names[i]
        rs = RequestService(
            request_id=new_request.id,
            service_id=sid,
            service_type_name=sname,
        )
        db.add(rs)
    db.commit()

    service_id = request_data.service_ids[0] if request_data.service_ids else None
    best_tech = (
        find_best_technician(db, service_id, request_data.lat, request_data.lng, excluded_ids=[])
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
        try:
            apply_request_status_transition(new_request, "assigned")
        except InvalidRequestStatusTransition as e:
            raise HTTPException(status_code=400, detail=str(e))
        db.commit()
        db.refresh(assignment)

        from app.services.firebase_service import notify_user

        notify_user(
            db=db,
            user_id=best_tech.id,
            user_type="technician",
            title="New service request",
            body="You have a new service request. Please respond within 5 minutes.",
            type="new_request",
            data={"request_id": str(new_request.id)},
        )

        schedule_assignment_timeout(new_request.id, assignment.id, SessionLocal)
    else:
        db.commit()

    db.refresh(new_request)
    _sync_request_realtime_state(new_request, db)
    payload = build_request_response(new_request, db)
    return payload


@router.post("/{request_id}/accept", response_model=RequestResponse)
@router.post("/{request_id}/accept/", response_model=RequestResponse, include_in_schema=False)
def accept_request(
    request_id: int,
    raw_request: Request,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    _reject_legacy_wrapped_query_param(raw_request)

    request = db.query(RequestModel).filter(RequestModel.id == request_id).with_for_update().first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    current_tech = (
        db.query(Technician).filter(Technician.id == technician_id).with_for_update().first()
    )
    if not current_tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    _ensure_technician_has_fresh_location(db, current_tech)

    if request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")

    active_request = _get_active_request_for_technician(
        db,
        technician_id,
        exclude_request_id=request_id,
        for_update=True,
    )
    if active_request:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have an active request (#{active_request.id}). "
                "Complete or cancel it before accepting another request."
            ),
        )

    assignment = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.request_id == request_id,
            RequestAssignment.technician_id == current_tech.id,
            RequestAssignment.status == "pending",
        )
        .with_for_update()
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=400, detail="No pending assignment found for this request")

    try:
        apply_request_status_transition(request, "accepted")
    except InvalidRequestStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e))

    assignment.status = "accepted"

    current_tech.availability_status = "busy"

    reassigned_notifications: list[tuple[int, int]] = []
    cancelled_notifications: list[tuple[int, int]] = []
    timeout_jobs: list[tuple[int, int]] = []

    other_pending_assignments = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.technician_id == current_tech.id,
            RequestAssignment.status == "pending",
            RequestAssignment.request_id != request_id,
        )
        .with_for_update()
        .all()
    )
    affected_request_ids = {row.request_id for row in other_pending_assignments}

    for pending_assignment in other_pending_assignments:
        pending_assignment.status = "cancelled"

    for affected_request_id in affected_request_ids:
        affected_request = (
            db.query(RequestModel)
            .filter(RequestModel.id == affected_request_id)
            .with_for_update()
            .first()
        )
        if not affected_request:
            continue

        if affected_request.assigned_technician_id != current_tech.id:
            continue

        if affected_request.status not in ("pending", "assigned"):
            continue

        excluded_ids = [
            row.technician_id
            for row in db.query(RequestAssignment)
            .filter(RequestAssignment.request_id == affected_request.id)
            .all()
        ]
        service_id = (
            affected_request.request_services[0].service_id
            if affected_request.request_services
            else None
        )
        next_tech = (
            find_best_technician(
                db,
                service_id,
                affected_request.lat,
                affected_request.lng,
                excluded_ids,
            )
            if service_id is not None
            else None
        )

        if next_tech:
            timeout_at = datetime.utcnow() + timedelta(minutes=5)
            new_assignment = RequestAssignment(
                request_id=affected_request.id,
                technician_id=next_tech.id,
                status="pending",
                timeout_at=timeout_at,
            )
            db.add(new_assignment)
            db.flush()

            affected_request.assigned_technician_id = next_tech.id
            try:
                apply_request_status_transition(
                    affected_request,
                    "assigned",
                    allow_same_status=True,
                    note="Reassigned because technician accepted another request",
                )
            except InvalidRequestStatusTransition as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

            reassigned_notifications.append((next_tech.id, affected_request.id))
            timeout_jobs.append((affected_request.id, new_assignment.id))
        else:
            affected_request.assigned_technician_id = None
            try:
                apply_request_status_transition(
                    affected_request,
                    "cancelled",
                    note="No available technicians after reassignment attempt",
                )
            except InvalidRequestStatusTransition as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

            cancelled_notifications.append((affected_request.customer_id, affected_request.id))

    _update_technician_acceptance_rate(db, current_tech.id)
    db.commit()

    db.refresh(request)
    db.refresh(current_tech)
    _sync_technician_realtime_state(current_tech)
    _sync_request_realtime_state(request, db)
    for affected_request_id in affected_request_ids:
        affected_request_state = (
            db.query(RequestModel).filter(RequestModel.id == affected_request_id).first()
        )
        if affected_request_state:
            _sync_request_realtime_state(affected_request_state, db)

    from app.services.firebase_service import notify_user

    for reassigned_tech_id, reassigned_request_id in reassigned_notifications:
        notify_user(
            db=db,
            user_id=reassigned_tech_id,
            user_type="technician",
            title="New service request",
            body="You have a new service request. Please respond within 5 minutes.",
            type="new_request",
            data={"request_id": str(reassigned_request_id)},
        )

    for cancelled_customer_id, cancelled_request_id in cancelled_notifications:
        notify_user(
            db=db,
            user_id=cancelled_customer_id,
            user_type="customer",
            title="No technicians available",
            body="Sorry, no technicians are currently available. Please try again later.",
            type="no_technicians",
            data={"request_id": str(cancelled_request_id)},
        )

    for timeout_request_id, timeout_assignment_id in timeout_jobs:
        schedule_assignment_timeout(timeout_request_id, timeout_assignment_id, SessionLocal)

    notify_user(
        db=db,
        user_id=request.customer_id,
        user_type="customer",
        title="Your request was accepted",
        body="The technician is on the way",
        type="request_accepted",
        data={"request_id": str(request_id)},
    )

    payload = build_request_response(request, db)
    return payload


@router.post("/{request_id}/reject", response_model=RequestResponse)
@router.post("/{request_id}/reject/", response_model=RequestResponse, include_in_schema=False)
def reject_request(
    request_id: int,
    body: RequestReject,
    raw_request: Request,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    _reject_legacy_wrapped_query_param(raw_request)

    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    current_tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if not current_tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    if request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")

    if request.status != "assigned":
        raise HTTPException(status_code=400, detail="Only assigned requests can be rejected")

    assignment = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.request_id == request_id,
            RequestAssignment.technician_id == current_tech.id,
            RequestAssignment.status == "pending",
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=400, detail="No pending assignment found for this request")

    reject_data = body
    reject_reason = str(reject_data.reason).strip()
    if not reject_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    assignment.status = "rejected"
    assignment.reject_reason = reject_reason
    assignment.rejected_at = datetime.utcnow()
    _set_technician_available_if_location_fresh(current_tech)
    _update_technician_acceptance_rate(db, current_tech.id)

    excluded_ids = [
        row.technician_id
        for row in db.query(RequestAssignment).filter(RequestAssignment.request_id == request_id).all()
    ]
    service_id = request.request_services[0].service_id if request.request_services else None
    next_tech = (
        find_best_technician(db, service_id, request.lat, request.lng, excluded_ids)
        if service_id is not None
        else None
    )

    if next_tech:
        timeout_at = datetime.utcnow() + timedelta(minutes=5)
        new_assignment = RequestAssignment(
            request_id=request.id,
            technician_id=next_tech.id,
            status="pending",
            timeout_at=timeout_at,
        )
        db.add(new_assignment)
        request.assigned_technician_id = next_tech.id
        try:
            apply_request_status_transition(
                request,
                "assigned",
                allow_same_status=True,
                note="Technician rejected assignment, reassigning request",
            )
        except InvalidRequestStatusTransition as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        db.commit()
        db.refresh(new_assignment)
        db.refresh(request)
        _sync_technician_realtime_state(current_tech)
        _sync_technician_realtime_state(next_tech)
        _sync_request_realtime_state(request, db)

        from app.services.firebase_service import notify_user

        notify_user(
            db=db,
            user_id=next_tech.id,
            user_type="technician",
            title="New service request",
            body="You have a new service request. Please respond within 5 minutes.",
            type="new_request",
            data={"request_id": str(request.id)},
        )
        schedule_assignment_timeout(request.id, new_assignment.id, SessionLocal)
    else:
        request.assigned_technician_id = None
        try:
            apply_request_status_transition(
                request,
                "cancelled",
                note="No available technicians after rejection",
            )
        except InvalidRequestStatusTransition as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

        db.commit()
        db.refresh(request)
        _sync_technician_realtime_state(current_tech)
        _sync_request_realtime_state(request, db)

        from app.services.firebase_service import notify_user

        notify_user(
            db=db,
            user_id=request.customer_id,
            user_type="customer",
            title="No technicians available",
            body="Sorry, no technicians are currently available. Please try again later.",
            type="no_technicians",
            data={"request_id": str(request.id)},
        )

    payload = build_request_response(request, db)
    return payload


@router.post("/{request_id}/cancel", response_model=RequestResponse)
@router.post("/{request_id}/cancel/", response_model=RequestResponse, include_in_schema=False)
def cancel_request(
    request_id: int,
    raw_request: Request,
    body: RequestCancel | None = None,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
):
    _reject_legacy_wrapped_query_param(raw_request)

    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cancel_data = body
    cancel_reason = str(cancel_data.reason).strip() if cancel_data and cancel_data.reason else ""
    assigned_tech_id = request.assigned_technician_id
    assigned_tech = None

    try:
        apply_request_status_transition(
            request,
            "cancelled",
            allow_same_status=True,
            note="Cancelled by customer",
        )
    except InvalidRequestStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e))

    affected_technician_ids: set[int] = set()
    pending_assignments = (
        db.query(RequestAssignment)
        .filter(
            RequestAssignment.request_id == request_id,
            RequestAssignment.status == "pending",
        )
        .all()
    )
    for assignment in pending_assignments:
        assignment.status = "cancelled"
        affected_technician_ids.add(assignment.technician_id)

    if assigned_tech_id is not None:
        tech = db.query(Technician).filter(Technician.id == assigned_tech_id).first()
        if tech:
            _set_technician_available_if_location_fresh(tech)
            assigned_tech = tech
        affected_technician_ids.add(assigned_tech_id)
        request.assigned_technician_id = None

    for tid in affected_technician_ids:
        _update_technician_acceptance_rate(db, tid)

    db.commit()
    db.refresh(request)
    _sync_request_realtime_state(request, db)
    _sync_technician_realtime_state(assigned_tech)

    if assigned_tech_id is not None:
        from app.services.firebase_service import notify_user

        body_text = "The customer cancelled this request."
        if cancel_reason:
            body_text = f"{body_text} Reason: {cancel_reason}"
        notify_user(
            db=db,
            user_id=assigned_tech_id,
            user_type="technician",
            title="Request cancelled",
            body=body_text,
            type="request_cancelled",
            data={"request_id": str(request.id)},
        )

    payload = build_request_response(request, db)
    return payload


@router.post("/{request_id}/complete", response_model=RequestResponse)
@router.post("/{request_id}/complete/", response_model=RequestResponse, include_in_schema=False)
def complete_request(
    request_id: int,
    body: RequestComplete,
    raw_request: Request,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
):
    _reject_legacy_wrapped_query_param(raw_request)

    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")
    try:
        apply_request_status_transition(request, "completed")
    except InvalidRequestStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e))

    complete_data = body
    request.technician_report = complete_data.report.strip()

    current_tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if current_tech:
        _set_technician_available_if_location_fresh(current_tech)

        total_accepted = (
            db.query(RequestAssignment)
            .filter(
                RequestAssignment.technician_id == current_tech.id,
                RequestAssignment.status == "accepted",
            )
            .count()
        )
        total_completed = (
            db.query(RequestModel)
            .filter(
                RequestModel.assigned_technician_id == current_tech.id,
                RequestModel.status == "completed",
            )
            .count()
        )
        current_tech.completion_rate = total_completed / total_accepted if total_accepted > 0 else 0

    db.commit()
    db.refresh(request)
    _sync_request_realtime_state(request, db)
    _sync_technician_realtime_state(current_tech)

    from app.services.firebase_service import notify_user

    notify_user(
        db=db,
        user_id=request.customer_id,
        user_type="customer",
        title="Your request is completed",
        body="The technician completed your request. Please rate the service.",
        type="request_completed",
        data={"request_id": str(request_id)},
    )

    payload = build_request_response(request, db)
    return payload


@router.post("/{request_id}/rate", response_model=RequestResponse)
@router.post("/{request_id}/rate/", response_model=RequestResponse, include_in_schema=False)
def rate_request(
    request_id: int,
    body: RequestRate,
    raw_request: Request,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
):
    _reject_legacy_wrapped_query_param(raw_request)

    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if request.status != "completed":
        raise HTTPException(status_code=400, detail="You can only rate completed requests")

    rate_data = body

    if request.customer_rating is not None:
        payload = build_request_response(request, db)
        return payload

    rating_value = float(rate_data.rating)
    comment = rate_data.comment

    request.customer_rating = rating_value
    request.rating_comment = str(comment).strip() if comment is not None and str(comment).strip() else None

    tech = None
    if request.assigned_technician_id is not None:
        db.add(
            Rating(
                customer_id=customer_id,
                technician_id=request.assigned_technician_id,
                score=rating_value,
                comment=request.rating_comment,
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
            title="New rating",
            body=f"You received a rating of {rating_value} out of 5",
            type="request_rated",
            data={"request_id": str(request_id)},
        )

    db.refresh(request)
    payload = build_request_response(request, db)
    return payload
