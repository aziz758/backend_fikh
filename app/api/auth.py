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
)
from app.schemas.customer import CustomerCreate
from app.schemas.technician import TechnicianCreate
from app.models import Customer, Technician
from app.models.technician import TechnicianService
from app.api.dependencies import get_current_user_id
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp,
    save_otp,
    verify_otp,
    get_user_by_phone,
)
from app.services.sms_service import send_otp_sms

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-otp")
async def send_otp(body: PhoneRequest, db: Session = Depends(get_db)):
    code = generate_otp()
    save_otp(db, body.phone, code, body.user_type)
    try:
        sent = await send_otp_sms(body.phone, code)
        if not sent:
            raise HTTPException(status_code=500, detail="فشل إرسال رمز التحقق، حاول مجدداً")
    except HTTPException:
        raise HTTPException(status_code=500, detail="فشل إرسال رمز التحقق، حاول مجدداً")
    return {"message": "تم إرسال رمز التحقق"}


@router.post("/verify-otp")
def verify_otp_endpoint(body: OtpVerify, db: Session = Depends(get_db)):
    if not verify_otp(db, body.phone, body.code, body.user_type):
        raise HTTPException(status_code=400, detail="رمز غير صحيح أو منتهي")
    user = get_user_by_phone(db, body.phone, body.user_type)
    if not user:
        return {"verified": True, "registered": False, "phone": body.phone}
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
    if db.query(Customer).filter(Customer.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="هذا الرقم مسجل مسبقاً")
    if db.query(Technician).filter(Technician.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="هذا الرقم مسجل مسبقاً")
    customer = Customer(
        name=body.name,
        phone=body.phone,
        password_hash=hash_password(body.password),
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
    if db.query(Technician).filter(Technician.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="هذا الرقم مسجل مسبقاً")
    if db.query(Customer).filter(Customer.phone == body.phone).first():
        raise HTTPException(status_code=400, detail="هذا الرقم مسجل مسبقاً")
    tech = Technician(
        name=body.name,
        phone=body.phone,
        password_hash=hash_password(body.password),
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)
    for sid in body.service_ids:
        link = TechnicianService(technician_id=tech.id, service_id=sid)
        db.add(link)
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
        raise HTTPException(status_code=401, detail="رقم الهاتف أو كلمة المرور غير صحيحة")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="رقم الهاتف أو كلمة المرور غير صحيحة")
    token = create_access_token(
        {"user_id": user.id, "user_type": body.user_type, "sub": body.phone}
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        user_type=body.user_type,
    )


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    # الفرونت الحالي لا يرسل user_type هنا، فنحاول التحقق على النوعين
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
        raise HTTPException(status_code=400, detail="رمز غير صحيح أو منتهي")

    user = get_user_by_phone(db, body.phone, verified_type)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router.post("/change-password")
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
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "تم تغيير كلمة المرور بنجاح"}
