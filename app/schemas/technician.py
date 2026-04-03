from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TechnicianCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=6)
    service_ids: list[int] = Field(default_factory=list)


class TechnicianResponse(BaseModel):
    id: int
    name: str
    phone: str
    status: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    avg_rating: Optional[float] = None
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class TechnicianNearbyQuery(BaseModel):
    service_id: int
    customer_lat: float
    customer_lng: float
    limit: int = 10
