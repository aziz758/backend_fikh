from pydantic import BaseModel, Field
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
    lat: float
    lng: float
