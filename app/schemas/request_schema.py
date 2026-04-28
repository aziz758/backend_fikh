from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: Optional[str] = None
    image_url: Optional[str] = None
    service_ids: List[int] = Field(..., min_length=1)
    service_type_names: Optional[List[str]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    governorate_id: Optional[int] = Field(default=None, gt=0)
    district_id: Optional[int] = Field(default=None, gt=0)


class RequestComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: str = Field(..., min_length=1)


class RequestRate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: float = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class RequestCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = None


class RequestReject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=2, max_length=300)


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
    governorate_id: Optional[int] = None
    governorate_name: Optional[str] = None
    district_id: Optional[int] = None
    district_name: Optional[str] = None

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
    latest_reject_reason: Optional[str] = None
    latest_rejected_at: Optional[datetime] = None
    google_maps_directions_url: Optional[str] = None
    apple_maps_directions_url: Optional[str] = None
    google_navigation_uri: Optional[str] = None
    geo_navigation_uri: Optional[str] = None

    class Config:
        from_attributes = True


class RequestListResponse(BaseModel):
    results: List[RequestResponse] = Field(default_factory=list)
    total: int
    page: int
    limit: int
