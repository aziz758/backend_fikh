from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Technician
from app.services.auth_service import decode_token

security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is required")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("user_id")
    user_type = payload.get("user_type")
    if not user_id or user_type not in {"customer", "technician"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if user_type == "customer":
        user = db.query(Customer).filter(Customer.id == user_id).first()
    else:
        user = db.query(Technician).filter(Technician.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if getattr(user, "status", None) == "inactive":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    return user_id, user_type


def _is_admin_customer(db: Session, user_id: int) -> bool:
    try:
        row = db.execute(
            text("SELECT is_admin FROM customers WHERE id = :user_id LIMIT 1"),
            {"user_id": user_id},
        ).first()
    except Exception:
        return False

    if not row:
        return False

    return bool(row[0])


def get_current_user(
    creds=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user_id, user_type = creds
    if user_type == "customer" and user_id and _is_admin_customer(db, user_id):
        return {"id": user_id, "type": "admin"}
    return {"id": user_id, "type": user_type}


def require_customer(creds=Depends(get_current_user_id)):
    user_id, user_type = creds
    if user_type != "customer":
        raise HTTPException(status_code=403, detail="Customer account required")
    return user_id


def require_technician(creds=Depends(get_current_user_id)):
    user_id, user_type = creds
    if user_type != "technician":
        raise HTTPException(status_code=403, detail="Technician account required")
    return user_id
