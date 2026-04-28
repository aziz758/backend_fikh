from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    PhoneRequest,
    OtpVerify,
    LoginRequest,
    TokenResponse,
    ResetPasswordRequest,
    ChangePasswordRequest,
    FcmTokenUpdateRequest,
)
from app.schemas.common import MessageResponse, SuccessResponse
from app.schemas.customer import CustomerCreate
from app.schemas.technician import TechnicianCreate
from app.models import Customer, Technician
from app.models.technician import TechnicianService, TechnicianServiceRequest
from app.api.dependencies import get_current_user, get_current_user_id
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_registration_token,
    generate_otp,
    save_otp,
    verify_otp,
    verify_registration_token,
    get_user_by_phone,
)
from app.services.location_validation_service import validate_area_selection
from app.services.sms_service import send_otp_sms

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(body: PhoneRequest, db: Session = Depends(get_db)):
    code = generate_otp()
    save_otp(db, body.phone, code, body.user_type)
    try:
        sent = await send_otp_sms(body.phone, code)
        if not sent:
            raise HTTPException(status_code=500, detail="Failed to send verification code. Please try again.")
    except HTTPException:
        raise HTTPException(status_code=500, detail="Failed to send verification code. Please try again.")
    return {"message": "Verification code sent"}


@router.post("/verify-otp")
def verify_otp_endpoint(body: OtpVerify, db: Session = Depends(get_db)):
    if not verify_otp(db, body.phone, body.code, body.user_type):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    user = get_user_by_phone(db, body.phone, body.user_type)
    if not user:
        registration_token = create_registration_token(body.phone, body.user_type)
        return {
            "verified": True,
            "registered": False,
            "phone": body.phone,
            "registration_token": registration_token,
        }
    if getattr(user, "status", None) == "inactive":
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = create_access_token(
        {"user_id": user.id, "user_type": body.user_type, "sub": body.phone}
    )
    return {
        "verified": True,
        "registered": True,
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_type": body.user_type,
    }


@router.post("/register/customer")
def register_customer(body: CustomerCreate, db: Session = Depends(get_db)):
    if not verify_registration_token(body.registration_token, body.phone, "customer"):
        raise HTTPException(status_code=400, detail="Invalid or expired registration token")
    if db.query(Customer).filter(Customer.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="This phone number is already registered")
    if db.query(Technician).filter(Technician.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="This phone number is already registered")
    validate_area_selection(
        db,
        governorate_id=body.governorate_id,
        district_id=body.district_id,
    )
    customer = Customer(
        name=body.name,
        phone=body.phone,
        password_hash=hash_password(body.password),
        governorate_id=body.governorate_id,
        district_id=body.district_id,
        address_details=body.address_details,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    token = create_access_token(
        {"user_id": customer.id, "user_type": "customer", "sub": body.phone}
    )
    return TokenResponse(
        access_token=token,
        user_id=customer.id,
        user_type="customer",
    )


@router.post("/register/technician")
def register_technician(body: TechnicianCreate, db: Session = Depends(get_db)):
    if not verify_registration_token(body.registration_token, body.phone, "technician"):
        raise HTTPException(status_code=400, detail="Invalid or expired registration token")
    if db.query(Technician).filter(Technician.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="This phone number is already registered")
    if db.query(Customer).filter(Customer.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="This phone number is already registered")
    tech = Technician(
        name=body.name,
        phone=body.phone,
        password_hash=hash_password(body.password),
        status="pending_documents",
        availability_status="offline",
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)
    for sid in body.service_ids:
        link = TechnicianService(technician_id=tech.id, service_id=sid)
        db.add(link)
    custom_service_name = body.custom_service_name or body.other_service_name
    if custom_service_name:
        db.add(
            TechnicianServiceRequest(
                technician_id=tech.id,
                requested_name=custom_service_name,
                status="pending",
            )
        )
    db.commit()
    token = create_access_token(
        {"user_id": tech.id, "user_type": "technician", "sub": body.phone}
    )
    return TokenResponse(
        access_token=token,
        user_id=tech.id,
        user_type="technician",
    )


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_phone(db, body.phone, body.user_type)
    if not user:
        raise HTTPException(status_code=401, detail="Phone number or password is incorrect")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Phone number or password is incorrect")
    if getattr(user, "status", None) == "inactive":
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = create_access_token(
        {"user_id": user.id, "user_type": body.user_type, "sub": body.phone}
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        user_type=body.user_type,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    # The current frontend does not send user_type here, so we try both types.
    if body.user_type:
        types = [body.user_type]
    else:
        types = ["customer", "technician"]

    verified = False
    verified_type = None
    for t in types:
        if verify_otp(db, body.phone, body.code, t):
            verified = True
            verified_type = t
            break

    if not verified or not verified_type:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = get_user_by_phone(db, body.phone, verified_type)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    body: ChangePasswordRequest,
    creds=Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user_id, user_type = creds
    user = None
    if user_type == "customer":
        user = db.query(Customer).filter(Customer.id == user_id).first()
    elif user_type == "technician":
        user = db.query(Technician).filter(Technician.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/update-fcm-token", response_model=SuccessResponse)
def update_fcm_token(
    body: FcmTokenUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update FCM token for push notifications."""
    fcm_token = body.fcm_token

    if current_user["type"] == "customer":
        user = db.query(Customer).filter(Customer.id == current_user["id"]).first()
    elif current_user["type"] == "technician":
        user = db.query(Technician).filter(Technician.id == current_user["id"]).first()
    else:
        user = None

    if user:
        user.fcm_token = fcm_token
        db.commit()

    return {"success": True}
