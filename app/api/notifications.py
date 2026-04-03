from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.notification import Notification

router = APIRouter()


@router.get("/")
def get_notifications(
    unread_only: int = 0,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(
        Notification.user_id == current_user["id"],
        Notification.user_type == current_user["type"],
    )
    if unread_only == 1:
        query = query.filter(Notification.is_read.is_(False))

    notifications = query.order_by(Notification.created_at.desc()).all()
    results = [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": str(n.created_at),
        }
        for n in notifications
    ]
    return {"results": results}


@router.post("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user["id"],
            Notification.user_type == current_user["type"],
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.commit()
    return {"success": True}


@router.post("/read-all")
def mark_all_read(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user["id"],
            Notification.user_type == current_user["type"],
            Notification.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"success": True, "updated": updated}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user["id"],
            Notification.user_type == current_user["type"],
        )
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notif)
    db.commit()
    return {"success": True}
