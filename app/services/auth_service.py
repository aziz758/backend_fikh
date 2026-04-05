from datetime import datetime, timedelta
import random
import string
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Customer, Technician, OtpVerification

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def save_otp(db: Session, phone: str, code: str, user_type: str) -> OtpVerification:
    db.query(OtpVerification).filter(
        OtpVerification.phone == phone,
        OtpVerification.user_type == user_type,
    ).delete(synchronize_session=False)
    otp = OtpVerification(
        phone=phone,
        code=code,
        user_type=user_type,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp


def verify_otp(db: Session, phone: str, code: str, user_type: str) -> bool:
    otp = (
        db.query(OtpVerification)
        .filter(
            OtpVerification.phone == phone,
            OtpVerification.code == code,
            OtpVerification.user_type == user_type,
            OtpVerification.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if otp is None:
        return False
    # Consume/invalidate OTP after successful verification to prevent reuse.
    db.delete(otp)
    db.commit()
    return True


def get_user_by_phone(db: Session, phone: str, user_type: str):
    if user_type == "customer":
        return db.query(Customer).filter(Customer.phone == phone).first()
    return db.query(Technician).filter(Technician.phone == phone).first()
