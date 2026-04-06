import asyncio
import logging
import threading
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.request_assignment import RequestAssignment
from app.models.technician import Technician, TechnicianService
from app.services.request_state_machine import (
    InvalidRequestStatusTransition,
    apply_request_status_transition,
)

logger = logging.getLogger(__name__)


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


def find_best_technician(
    db: Session,
    service_id: int,
    customer_lat: float | None,
    customer_lng: float | None,
    excluded_ids: list | None = None,
):
    """Pick an approved + available technician that provides the requested service."""
    excluded_ids = excluded_ids or []

    query = (
        db.query(Technician)
        .join(TechnicianService, Technician.id == TechnicianService.technician_id)
        .filter(
            TechnicianService.service_id == service_id,
            Technician.status == "approved",
            or_(Technician.availability_status == "available", Technician.availability_status.is_(None)),
        )
    )
    if excluded_ids:
        query = query.filter(Technician.id.notin_(excluded_ids))

    # Selection is based on service match + availability only (no distance/rating score).
    return query.order_by(Technician.id.asc()).first()


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

            from app.services.firebase_service import notify_user

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

            from app.services.firebase_service import notify_user

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
