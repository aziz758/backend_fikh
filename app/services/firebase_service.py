import logging

import firebase_admin
from firebase_admin import credentials, messaging

from app.config import settings

logger = logging.getLogger(__name__)


try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase initialized successfully")
except Exception as e:
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
