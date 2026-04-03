from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import decode_token

security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token مطلوب")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token غير صالح")
    return payload.get("user_id"), payload.get("user_type")


def require_customer(creds=Depends(get_current_user_id)):
    user_id, user_type = creds
    if user_type != "customer":
        raise HTTPException(status_code=403, detail="يتطلب حساب عميل")
    return user_id


def require_technician(creds=Depends(get_current_user_id)):
    user_id, user_type = creds
    if user_type != "technician":
        raise HTTPException(status_code=403, detail="يتطلب حساب فني")
    return user_id
