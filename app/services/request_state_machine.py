from datetime import datetime


REQUEST_STATUS_PENDING = "pending"
REQUEST_STATUS_ASSIGNED = "assigned"
REQUEST_STATUS_ACCEPTED = "accepted"
REQUEST_STATUS_COMPLETED = "completed"
REQUEST_STATUS_CANCELLED = "cancelled"

REQUEST_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    REQUEST_STATUS_PENDING: {REQUEST_STATUS_ASSIGNED, REQUEST_STATUS_CANCELLED},
    REQUEST_STATUS_ASSIGNED: {REQUEST_STATUS_ACCEPTED, REQUEST_STATUS_CANCELLED},
    REQUEST_STATUS_ACCEPTED: {REQUEST_STATUS_COMPLETED, REQUEST_STATUS_CANCELLED},
    REQUEST_STATUS_COMPLETED: set(),
    REQUEST_STATUS_CANCELLED: set(),
}


class InvalidRequestStatusTransition(ValueError):
    def __init__(self, current: str, target: str, allowed: set[str], note: str | None = None):
        allowed_text = ", ".join(sorted(allowed)) if allowed else "none"
        msg = (
            f"Invalid request status transition: {current} -> {target}. "
            f"Allowed next statuses: {allowed_text}."
        )
        if note:
            msg = f"{msg} {note}"
        super().__init__(msg)


def get_allowed_next_statuses(current_status: str) -> set[str]:
    return REQUEST_ALLOWED_TRANSITIONS.get(current_status, set())


def apply_request_status_transition(
    request_obj,
    to_status: str,
    *,
    allow_same_status: bool = False,
    note: str | None = None,
) -> None:
    current_status = (getattr(request_obj, "status", None) or REQUEST_STATUS_PENDING).strip()
    allowed_next = get_allowed_next_statuses(current_status)

    if current_status == to_status:
        if not allow_same_status:
            raise InvalidRequestStatusTransition(current_status, to_status, allowed_next, note=note)
    elif to_status not in allowed_next:
        raise InvalidRequestStatusTransition(current_status, to_status, allowed_next, note=note)

    request_obj.status = to_status
    now = datetime.utcnow()

    if to_status == REQUEST_STATUS_ASSIGNED:
        request_obj.assigned_at = now
    elif to_status == REQUEST_STATUS_ACCEPTED:
        if getattr(request_obj, "assigned_at", None) is None:
            request_obj.assigned_at = now
        request_obj.accepted_at = now
    elif to_status == REQUEST_STATUS_COMPLETED:
        if getattr(request_obj, "accepted_at", None) is None:
            request_obj.accepted_at = now
        request_obj.completed_at = now
