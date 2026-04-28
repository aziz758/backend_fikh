from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime


class TechnicianCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=6)
    registration_token: str = Field(..., min_length=20)
    service_ids: list[int] = Field(default_factory=list)
    custom_service_name: Optional[str] = Field(default=None, max_length=150)
    other_service_name: Optional[str] = Field(default=None, max_length=150)

    @field_validator("custom_service_name", "other_service_name", mode="before")
    @classmethod
    def validate_custom_service_name(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        if len(cleaned) < 2:
            raise ValueError("custom service name must be at least 2 characters")
        return cleaned

    @model_validator(mode="after")
    def validate_custom_service_aliases(self):
        if (
            self.custom_service_name
            and self.other_service_name
            and self.custom_service_name != self.other_service_name
        ):
            raise ValueError("custom_service_name and other_service_name must match when both are provided")
        return self


class TechnicianResponse(BaseModel):
    id: int
    name: str
    phone: str
    status: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    governorate_id: Optional[int] = None
    governorate_name: Optional[str] = None
    district_id: Optional[int] = None
    district_name: Optional[str] = None
    address_details: Optional[str] = None
    avg_rating: Optional[float] = None
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class TechnicianNearbyQuery(BaseModel):
    service_id: int
    customer_lat: float
    customer_lng: float
    limit: int = 10
