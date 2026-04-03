from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RequestCreate(BaseModel):
    note: Optional[str] = None
    image_url: Optional[str] = None
    service_ids: List[int] = Field(..., min_length=1)
    service_type_names: Optional[List[str]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None


class RequestResponse(BaseModel):
    id: int
    customer_id: int
    note: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    # مشتقات لخدمة الفرونت
    service_ids: List[int] = []
    service_type_names: List[str] = []
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None

    assigned_technician_id: Optional[int] = None
    assigned_technician_name: Optional[str] = None
    assigned_technician_rating: Optional[float] = None
    technician_report: Optional[str] = None
    customer_rating: Optional[float] = None

    class Config:
        from_attributes = True
