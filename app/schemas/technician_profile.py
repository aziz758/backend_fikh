from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TechnicianProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    status: str | None = None
    availability_status: str | None = None
    lat: float | None = None
    lng: float | None = None
    governorate_id: int | None = None
    governorate_name: str | None = None
    district_id: int | None = None
    district_name: str | None = None
    address_details: str | None = None
    location_updated_at: datetime | None = None
    service_radius_km: float | None = None
    work_start_time: str | None = None
    work_end_time: str | None = None
    work_days: list[int] = Field(default_factory=list)
    avg_rating: float = 0.0
    total_ratings: int = 0
    acceptance_rate: float = 0.0
    completion_rate: float = 0.0
    profile_photo_url: str | None = None
    id_card_photo_url: str | None = None


class TechnicianProfileStatusResponse(BaseModel):
    status: str | None = None


class TechnicianDocumentsUploadResponse(BaseModel):
    success: bool
    status: str


class TechnicianLocationUpdateRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class TechnicianLocationUpdateResponse(BaseModel):
    success: bool
    lat: float
    lng: float
    location_updated_at: datetime | None = None
    availability_status: str | None = None


class TechnicianAreaUpdateRequest(BaseModel):
    governorate_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    address_details: str | None = Field(default=None, max_length=255)

    @field_validator("address_details")
    @classmethod
    def validate_address_details(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TechnicianServiceAreaInput(BaseModel):
    governorate_id: int = Field(..., gt=0)
    district_id: int | None = Field(default=None, gt=0)


class TechnicianServiceAreasUpdateRequest(BaseModel):
    service_areas: list[TechnicianServiceAreaInput] = Field(..., min_length=1, max_length=50)


class TechnicianServiceAreaResponse(BaseModel):
    id: int
    governorate_id: int
    governorate_name: str | None = None
    district_id: int | None = None
    district_name: str | None = None
    scope: Literal["governorate", "district"]


class TechnicianAvailabilityUpdateRequest(BaseModel):
    availability_status: Literal["available", "on_break"]


class TechnicianAvailabilityUpdateResponse(BaseModel):
    success: bool
    availability_status: str


class TechnicianWorkSettingsUpdateRequest(BaseModel):
    service_radius_km: float = Field(..., gt=0, le=200)
    work_start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    work_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    work_days: list[int] = Field(..., min_length=1, max_length=7)


class TechnicianWorkSettingsUpdateResponse(BaseModel):
    success: bool
    service_radius_km: float
    work_start_time: str
    work_end_time: str
    work_days: list[int]
