from pydantic import BaseModel, Field


class PhoneRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    user_type: str = Field(..., pattern="^(customer|technician)$")


class OtpVerify(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=6)
    user_type: str = Field(..., pattern="^(customer|technician)$")


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=6)
    user_type: str = Field(..., pattern="^(customer|technician)$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    user_type: str


class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=6)
    new_password: str = Field(..., min_length=6)
    # اختياري لتوافق أفضل مع الفرونت الحالي (الذي لا يرسل user_type)
    user_type: str | None = Field(default=None, pattern="^(customer|technician)$")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
