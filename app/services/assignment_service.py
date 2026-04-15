import asyncio
import logging
import math
import threading
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.request_assignment import RequestAssignment
from app.models.technician import Technician, TechnicianService
from app.services.location_service import (
    location_cutoff_utc,
    mark_stale_available_technicians_offline,
)
from app.services.request_state_machine import (
    InvalidRequestStatusTransition,
    apply_request_status_transition,
)
from app.services.technician_priority_service import compute_technician_priority_score
from app.services.technician_schedule_service import (
    is_technician_within_working_hours,
    resolve_service_radius_km,
)

logger = logging.getLogger(__name__)
TECHNICIAN_ACTIVE_REQUEST_STATUSES = ("accepted",)


def _recalc_acceptance_rate(db: Session, technician_id: int) -> None:
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


def _haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    lat1_rad, lng1_rad, lat2_rad, lng2_rad = map(
        math.radians,
        [lat1, lng1, lat2, lng2],
    )
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return r * c


def find_best_technician(
    db: Session,
    service_id: int,
    customer_lat: float | None,
    customer_lng: float | None,
    excluded_ids: list | None = None,
):
    """Pick an approved + available technician with fresh location and no active request."""
    excluded_ids = excluded_ids or []
    cutoff = location_cutoff_utc()

    updated = mark_stale_available_technicians_offline(db)
    if updated > 0:
        db.commit()

    active_request_exists = (
        db.query(Request.id)
        .filter(
            Request.assigned_technician_id == Technician.id,
            Request.status.in_(TECHNICIAN_ACTIVE_REQUEST_STATUSES),
        )
        .exists()
    )

    query = (
        db.query(Technician)
        .join(TechnicianService, Technician.id == TechnicianService.technician_id)
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
    )
    if excluded_ids:
        query = query.filter(Technician.id.notin_(excluded_ids))

    candidates = query.order_by(Technician.id.asc()).all()
    if not candidates:
        return None

    candidates = [tech for tech in candidates if is_technician_within_working_hours(tech)]
    if not candidates:
        return None

    ranked: list[tuple[float, float | None, Technician]] = []
    for tech in candidates:
        tech_radius = resolve_service_radius_km(tech)
        distance = None
        if customer_lat is not None and customer_lng is not None and tech.lat is not None and tech.lng is not None:
            distance = _haversine_distance_km(customer_lat, customer_lng, float(tech.lat), float(tech.lng))
            if distance > tech_radius:
                continue

        score = compute_technician_priority_score(
            distance_km=distance,
            max_distance_km=tech_radius,
            avg_rating=getattr(tech, "avg_rating", 0.0),
            acceptance_rate=getattr(tech, "acceptance_rate", 0.0),
            completion_rate=getattr(tech, "completion_rate", 0.0),
        )
        ranked.append((score, distance, tech))

    if not ranked:
        return None

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1] if item[1] is not None else float("inf"),
            -(float(item[2].avg_rating or 0.0)),
            -(float(item[2].acceptance_rate or 0.0)),
            item[2].id,
        )
    )
    return ranked[0][2]


def schedule_assignment_timeout(request_id: int, assignment_id: int, db_factory) -> None:
    """
    Schedule timeout check safely for both async and sync route contexts.
    - If called inside event loop: create_task
    - Otherwise: run coroutine in a daemon thread
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(check_assignment_timeout(request_id, assignment_id, db_factory))
    except RuntimeError:

        def _runner():
            asyncio.run(check_assignment_timeout(request_id, assignment_id, db_factory))

        threading.Thread(target=_runner, daemon=True).start()


async def check_assignment_timeout(request_id: int, assignment_id: int, db_factory):
    """Background task: after 5 minutes, if not accepted, try next technician."""
    await asyncio.sleep(300)

    db = db_factory()
    try:
        assignment = db.query(RequestAssignment).filter(RequestAssignment.id == assignment_id).first()
        if not assignment or assignment.status != "pending":
            return

        assignment.status = "timeout"
        _recalc_acceptance_rate(db, assignment.technician_id)
        db.commit()

        request = db.query(Request).filter(Request.id == request_id).first()
        if not request or request.status not in ["pending", "assigned"]:
            return

        excluded_ids = [
            a.technician_id
            for a in db.query(RequestAssignment).filter(RequestAssignment.request_id == request_id).all()
        ]
        service_id = request.request_services[0].service_id if request.request_services else None
        if not service_id:
            return

        next_tech = find_best_technician(db, service_id, request.lat, request.lng, excluded_ids)
        if next_tech:
            timeout_at = datetime.utcnow() + timedelta(minutes=5)
            new_assignment = RequestAssignment(
                request_id=request_id,
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
                    note="Automatic reassignment after technician timeout",
                )
            except InvalidRequestStatusTransition as e:
                logger.error(f"Timeout reassignment transition error: {e}")
                return
            db.commit()

            from app.services.firebase_service import (
                notify_user,
                sync_request_realtime,
                sync_request_tracking_realtime,
            )

            sync_request_realtime(request)
            sync_request_tracking_realtime(request, next_tech)

            notify_user(
                db=db,
                user_id=next_tech.id,
                user_type="technician",
                title="New service request",
                body="You have a new service request. Please respond within 5 minutes.",
                type="new_request",
                data={"request_id": str(request_id)},
            )

            schedule_assignment_timeout(request_id, new_assignment.id, db_factory)
        else:
            try:
                apply_request_status_transition(
                    request,
                    "cancelled",
                    note="No available technicians after timeout cycle",
                )
            except InvalidRequestStatusTransition as e:
                logger.error(f"Timeout cancellation transition error: {e}")
                return
            db.commit()

            from app.services.firebase_service import (
                clear_request_tracking_realtime,
                notify_user,
                sync_request_realtime,
            )

            sync_request_realtime(request)
            clear_request_tracking_realtime(request_id, status=request.status)

            notify_user(
                db=db,
                user_id=request.customer_id,
                user_type="customer",
                title="No technicians available",
                body="Sorry, no technicians are currently available. Please try again later.",
                type="no_technicians",
                data={"request_id": str(request_id)},
            )
    except Exception as e:
        logger.error(f"Timeout check error: {e}")
    finally:
        db.close()
