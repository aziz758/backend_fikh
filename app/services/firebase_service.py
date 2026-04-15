import logging
from datetime import datetime, timezone
from typing import Any

import firebase_admin
from firebase_admin import credentials, db as realtime_db, messaging

from app.config import settings

logger = logging.getLogger(__name__)


_firebase_ready = False
_realtime_ready = False


try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        options = {}
        if settings.FIREBASE_DATABASE_URL:
            options["databaseURL"] = settings.FIREBASE_DATABASE_URL
        firebase_admin.initialize_app(cred, options=options if options else None)
    _firebase_ready = True
    _realtime_ready = bool(settings.FIREBASE_DATABASE_URL)
    logger.info("Firebase initialized successfully")
except Exception as e:
    _firebase_ready = False
    _realtime_ready = False
    logger.error(f"Firebase initialization failed: {e}")


def send_push_notification(fcm_token: str, title: str, body: str, data: dict | None = None):
    """Send FCM push notification to a single device."""
    if not fcm_token:
        return False

    payload = data or {}
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in payload.items()},
            token=fcm_token,
        )
        response = messaging.send(message)
        logger.info(f"FCM sent: {response}")
        return True
    except Exception as e:
        logger.error(f"FCM send failed: {e}")
        return False


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _realtime_set(path: str, payload: dict) -> bool:
    if not _realtime_ready:
        return False
    try:
        realtime_db.reference(path).set(payload)
        return True
    except Exception as e:
        logger.error(f"Firebase realtime set failed for '{path}': {e}")
        return False


def _realtime_update(path: str, payload: dict) -> bool:
    if not _realtime_ready:
        return False
    try:
        realtime_db.reference(path).update(payload)
        return True
    except Exception as e:
        logger.error(f"Firebase realtime update failed for '{path}': {e}")
        return False


def is_realtime_enabled() -> bool:
    return _realtime_ready


def sync_technician_realtime(technician_obj: Any) -> bool:
    technician_id = getattr(technician_obj, "id", None)
    if technician_id is None:
        return False
    payload = {
        "technician_id": int(technician_id),
        "status": getattr(technician_obj, "status", None),
        "availability_status": getattr(technician_obj, "availability_status", None),
        "lat": getattr(technician_obj, "lat", None),
        "lng": getattr(technician_obj, "lng", None),
        "location_updated_at": _to_iso(getattr(technician_obj, "location_updated_at", None)),
        "service_radius_km": getattr(technician_obj, "service_radius_km", None),
        "work_start_time": getattr(technician_obj, "work_start_time", None),
        "work_end_time": getattr(technician_obj, "work_end_time", None),
        "work_days": getattr(technician_obj, "work_days", None),
        "updated_at": _to_iso(datetime.utcnow()),
    }
    return _realtime_set(f"live/technicians/{int(technician_id)}", payload)


def sync_request_realtime(request_obj: Any) -> bool:
    request_id = getattr(request_obj, "id", None)
    if request_id is None:
        return False
    payload = {
        "request_id": int(request_id),
        "status": getattr(request_obj, "status", None),
        "customer_id": getattr(request_obj, "customer_id", None),
        "assigned_technician_id": getattr(request_obj, "assigned_technician_id", None),
        "lat": getattr(request_obj, "lat", None),
        "lng": getattr(request_obj, "lng", None),
        "address": getattr(request_obj, "address", None),
        "assigned_at": _to_iso(getattr(request_obj, "assigned_at", None)),
        "accepted_at": _to_iso(getattr(request_obj, "accepted_at", None)),
        "completed_at": _to_iso(getattr(request_obj, "completed_at", None)),
        "updated_at": _to_iso(datetime.utcnow()),
    }
    return _realtime_set(f"live/requests/{int(request_id)}", payload)


def sync_request_tracking_realtime(request_obj: Any, technician_obj: Any | None = None) -> bool:
    request_id = getattr(request_obj, "id", None)
    if request_id is None:
        return False

    if technician_obj is None:
        return False

    lat = getattr(technician_obj, "lat", None)
    lng = getattr(technician_obj, "lng", None)
    if lat is None or lng is None:
        return False

    payload = {
        "request_id": int(request_id),
        "status": getattr(request_obj, "status", None),
        "customer_id": getattr(request_obj, "customer_id", None),
        "technician_id": getattr(technician_obj, "id", None),
        "lat": lat,
        "lng": lng,
        "location_updated_at": _to_iso(getattr(technician_obj, "location_updated_at", None)),
        "updated_at": _to_iso(datetime.utcnow()),
        "active": getattr(request_obj, "status", None) in {"assigned", "accepted"},
    }
    return _realtime_set(f"live/request_tracking/{int(request_id)}", payload)


def clear_request_tracking_realtime(request_id: int, status: str | None = None) -> bool:
    payload = {
        "active": False,
        "ended_at": _to_iso(datetime.utcnow()),
        "updated_at": _to_iso(datetime.utcnow()),
    }
    if status:
        payload["status"] = status
    return _realtime_update(f"live/request_tracking/{int(request_id)}", payload)


def save_notification(db, user_id: int, user_type: str, title: str, body: str, type: str):
    """Save notification to database."""
    from app.models.notification import Notification

    notif = Notification(
        user_id=user_id,
        user_type=user_type,
        title=title,
        body=body,
        type=type,
    )
    db.add(notif)
    db.commit()
    return notif


def notify_user(
    db,
    user_id: int,
    user_type: str,
    title: str,
    body: str,
    type: str,
    data: dict | None = None,
):
    """Send FCM + save notification in DB."""
    payload = data or {}
    fcm_token = None

    if user_type == "customer":
        from app.models.customer import Customer

        user = db.query(Customer).filter(Customer.id == user_id).first()
        if user:
            fcm_token = getattr(user, "fcm_token", None)
    elif user_type == "technician":
        from app.models.technician import Technician

        user = db.query(Technician).filter(Technician.id == user_id).first()
        if user:
            fcm_token = getattr(user, "fcm_token", None)

    if fcm_token:
        send_push_notification(fcm_token, title, body, payload)

    return save_notification(db, user_id, user_type, title, body, type)
