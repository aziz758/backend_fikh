from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Customer, Technician, OtpVerification

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
REGISTRATION_TOKEN_EXPIRE_MINUTES = 15
OTP_HASH_LENGTH = 64


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


def create_registration_token(phone: str, user_type: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=REGISTRATION_TOKEN_EXPIRE_MINUTES)
    payload = {
        "purpose": "registration",
        "phone": phone,
        "user_type": user_type,
        "sub": phone,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_registration_token(token: str, phone: str, user_type: str) -> bool:
    payload = decode_token(token)
    if not payload:
        return False
    return (
        payload.get("purpose") == "registration"
        and payload.get("phone") == phone
        and payload.get("user_type") == user_type
    )


def generate_otp(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def _hash_otp(phone: str, code: str, user_type: str) -> str:
    message = f"{user_type}:{phone}:{code}".encode("utf-8")
    secret = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _otp_matches(stored_code: str, phone: str, code: str, user_type: str) -> bool:
    if len(stored_code) == OTP_HASH_LENGTH:
        expected_hash = _hash_otp(phone, code, user_type)
        return hmac.compare_digest(stored_code, expected_hash)

    # Temporary compatibility for unexpired OTP rows created before hashing.
    return hmac.compare_digest(stored_code, code)


def save_otp(db: Session, phone: str, code: str, user_type: str) -> OtpVerification:
    db.query(OtpVerification).filter(
        OtpVerification.phone == phone,
        OtpVerification.user_type == user_type,
    ).delete(synchronize_session=False)
    otp = OtpVerification(
        phone=phone,
        code=_hash_otp(phone, code, user_type),
        user_type=user_type,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp


def verify_otp(db: Session, phone: str, code: str, user_type: str) -> bool:
    otps = (
        db.query(OtpVerification)
        .filter(
            OtpVerification.phone == phone,
            OtpVerification.user_type == user_type,
            OtpVerification.expires_at > datetime.utcnow(),
        )
        .order_by(OtpVerification.created_at.desc())
        .all()
    )

    otp = None
    for candidate in otps:
        if _otp_matches(candidate.code, phone, code, user_type):
            otp = candidate
            break

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
