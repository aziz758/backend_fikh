from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


TechnicianAccountStatus = Literal["approved", "rejected", "pending_approval", "pending_documents"]
BroadcastTarget = Literal["all", "customers", "technicians", "specific"]


class TechnicianStatusUpdateRequest(BaseModel):
    status: TechnicianAccountStatus


class TechnicianStatusUpdateWithIdRequest(BaseModel):
    technician_id: int = Field(..., ge=1)
    status: TechnicianAccountStatus


class TechnicianServiceRequestApproveRequest(BaseModel):
    service_id: int | None = Field(default=None, ge=1)
    service_name: str | None = Field(default=None, max_length=100)
    admin_note: str | None = Field(default=None, max_length=1000)

    @field_validator("service_name", "admin_note", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None

    @model_validator(mode="after")
    def validate_service_choice(self):
        has_existing_service = self.service_id is not None
        has_new_service_name = self.service_name is not None
        if has_existing_service == has_new_service_name:
            raise ValueError("Send exactly one of service_id or service_name")
        return self


class TechnicianServiceRequestRejectRequest(BaseModel):
    admin_note: str = Field(..., min_length=1, max_length=1000)

    @field_validator("admin_note", mode="before")
    @classmethod
    def normalize_admin_note(cls, value):
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized


class BroadcastNotificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    target: BroadcastTarget = "all"
    user_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_specific_target(self):
        if self.target == "specific" and not self.user_ids:
            raise ValueError("user_ids is required for specific target")
        return self


class BroadcastNotificationResponse(BaseModel):
    success: bool
    sent_count: int
