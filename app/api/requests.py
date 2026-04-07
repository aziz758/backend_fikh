import os
import shutil
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
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
    RequestCancelWrapped,
    RequestComplete,
    RequestCompleteWrapped,
    RequestCreate,
    RequestCreateWrapped,
    RequestRate,
    RequestRateWrapped,
    RequestResponse,
)
from app.services.assignment_service import find_best_technician, schedule_assignment_timeout
from app.services.request_state_machine import (
    InvalidRequestStatusTransition,
    apply_request_status_transition,
)

router = APIRouter(prefix="/requests", tags=["requests"])
upload_router = APIRouter()


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

    os.makedirs("uploads", exist_ok=True)
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = f"uploads/{filename}"
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"image_url": f"/uploads/{filename}", "url": f"/uploads/{filename}"}


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


def _maybe_wrap_response(payload, wrapped: bool):
    if wrapped:
        return JSONResponse(content={"request": payload})
    return payload


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
    }


@router.get("/", response_model=list[RequestResponse])
def list_my_requests(
    creds=Depends(get_current_user_id),
    db: Session = Depends(get_db),
    wrapped: int = Query(default=0),
):
    user_id, user_type = creds
    q = db.query(RequestModel).order_by(RequestModel.created_at.desc())
    if user_type == "customer":
        q = q.filter(RequestModel.customer_id == user_id)
    elif user_type == "technician":
        q = q.filter(RequestModel.assigned_technician_id == user_id)
    else:
        raise HTTPException(status_code=403, detail="Unsupported user type")

    reqs = q.all()
    response = [build_request_response(r, db) for r in reqs]
    if wrapped == 1:
        return JSONResponse(content={"request": response})
    return response


@router.post("/", response_model=RequestResponse)
def create_request(
    body: RequestCreate | RequestCreateWrapped,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
    wrapped: int = Query(default=0),
):
    wrapped_body = isinstance(body, RequestCreateWrapped)
    request_data = body.request if wrapped_body else body

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
    response = build_request_response(new_request, db)
    return _maybe_wrap_response(response, wrapped == 1 or wrapped_body)


@router.post("/{request_id}/accept", response_model=RequestResponse)
@router.post("/{request_id}/accept/", response_model=RequestResponse, include_in_schema=False)
def accept_request(
    request_id: int,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
    wrapped: int = Query(default=0),
):
    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    current_tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if not current_tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    if request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")

    try:
        apply_request_status_transition(request, "accepted")
    except InvalidRequestStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e))

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

    assignment.status = "accepted"

    current_tech.availability_status = "busy"

    _update_technician_acceptance_rate(db, current_tech.id)
    db.commit()

    from app.services.firebase_service import notify_user

    notify_user(
        db=db,
        user_id=request.customer_id,
        user_type="customer",
        title="Your request was accepted",
        body="The technician is on the way",
        type="request_accepted",
        data={"request_id": str(request_id)},
    )

    db.refresh(request)
    response = build_request_response(request, db)
    return _maybe_wrap_response(response, wrapped == 1)


@router.post("/{request_id}/reject", response_model=RequestResponse)
@router.post("/{request_id}/reject/", response_model=RequestResponse, include_in_schema=False)
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
    wrapped: int = Query(default=0),
):
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

    assignment.status = "rejected"
    current_tech.availability_status = "available"
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

    db.refresh(request)
    response = build_request_response(request, db)
    return _maybe_wrap_response(response, wrapped == 1)


@router.post("/{request_id}/cancel", response_model=RequestResponse)
@router.post("/{request_id}/cancel/", response_model=RequestResponse, include_in_schema=False)
def cancel_request(
    request_id: int,
    body: RequestCancel | RequestCancelWrapped | None = None,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
    wrapped: int = Query(default=0),
):
    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    wrapped_body = isinstance(body, RequestCancelWrapped)
    cancel_data = body.request if wrapped_body else body
    cancel_reason = str(cancel_data.reason).strip() if cancel_data and cancel_data.reason else ""
    assigned_tech_id = request.assigned_technician_id

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
            tech.availability_status = "available"
        affected_technician_ids.add(assigned_tech_id)
        request.assigned_technician_id = None

    for tid in affected_technician_ids:
        _update_technician_acceptance_rate(db, tid)

    db.commit()

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

    db.refresh(request)
    response = build_request_response(request, db)
    return _maybe_wrap_response(response, wrapped == 1 or wrapped_body)


@router.post("/{request_id}/complete", response_model=RequestResponse)
@router.post("/{request_id}/complete/", response_model=RequestResponse, include_in_schema=False)
def complete_request(
    request_id: int,
    body: RequestComplete | RequestCompleteWrapped,
    db: Session = Depends(get_db),
    technician_id: int = Depends(require_technician),
    wrapped: int = Query(default=0),
):
    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.assigned_technician_id != technician_id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")
    try:
        apply_request_status_transition(request, "completed")
    except InvalidRequestStatusTransition as e:
        raise HTTPException(status_code=400, detail=str(e))

    wrapped_body = isinstance(body, RequestCompleteWrapped)
    complete_data = body.request if wrapped_body else body
    request.technician_report = complete_data.report.strip()

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
            db.query(RequestModel)
            .filter(
                RequestModel.assigned_technician_id == current_tech.id,
                RequestModel.status == "completed",
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
        title="Your request is completed",
        body="The technician completed your request. Please rate the service.",
        type="request_completed",
        data={"request_id": str(request_id)},
    )

    db.refresh(request)
    response = build_request_response(request, db)
    return _maybe_wrap_response(response, wrapped == 1 or wrapped_body)


@router.post("/{request_id}/rate", response_model=RequestResponse)
@router.post("/{request_id}/rate/", response_model=RequestResponse, include_in_schema=False)
def rate_request(
    request_id: int,
    body: RequestRate | RequestRateWrapped,
    db: Session = Depends(get_db),
    customer_id: int = Depends(require_customer),
    wrapped: int = Query(default=0),
):
    request = db.query(RequestModel).filter(RequestModel.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    if request.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if request.status != "completed":
        raise HTTPException(status_code=400, detail="You can only rate completed requests")

    wrapped_body = isinstance(body, RequestRateWrapped)
    rate_data = body.request if wrapped_body else body

    if request.customer_rating is not None:
        response = build_request_response(request, db)
        return _maybe_wrap_response(response, wrapped == 1 or wrapped_body)

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
    response = build_request_response(request, db)
    return _maybe_wrap_response(response, wrapped == 1 or wrapped_body)
