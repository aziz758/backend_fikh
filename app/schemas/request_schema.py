from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RequestCreate(BaseModel):
    note: Optional[str] = None
    image_url: Optional[str] = None
    service_ids: List[int] = Field(..., min_length=1)
    service_type_names: Optional[List[str]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None


class RequestCreateWrapped(BaseModel):
    request: RequestCreate


class RequestComplete(BaseModel):
    report: str = Field(..., min_length=1)


class RequestCompleteWrapped(BaseModel):
    request: RequestComplete


class RequestRate(BaseModel):
    rating: float = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class RequestRateWrapped(BaseModel):
    request: RequestRate


class RequestCancel(BaseModel):
    reason: Optional[str] = None


class RequestCancelWrapped(BaseModel):
    request: RequestCancel


class RequestResponse(BaseModel):
    id: int
    customer_id: int
    note: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    # Extra fields for frontend convenience.
    service_ids: List[int] = Field(default_factory=list)
    service_type_names: List[str] = Field(default_factory=list)
    service_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None

    assigned_technician_id: Optional[int] = None
    assigned_technician_name: Optional[str] = None
    assigned_technician_rating: Optional[float] = None
    assigned_technician_avatar: Optional[str] = None
    technician_report: Optional[str] = None
    customer_rating: Optional[float] = None
    rating_comment: Optional[str] = None
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
