from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=6)


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone: str
    status: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerUpdateLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be empty")
        return cleaned
