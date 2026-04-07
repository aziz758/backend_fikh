from typing import Literal

from pydantic import BaseModel, Field, model_validator


TechnicianAccountStatus = Literal["approved", "rejected", "pending_approval", "pending_documents"]
BroadcastTarget = Literal["all", "customers", "technicians", "specific"]


class TechnicianStatusUpdateRequest(BaseModel):
    status: TechnicianAccountStatus


class TechnicianStatusUpdateWithIdRequest(BaseModel):
    technician_id: int = Field(..., ge=1)
    status: TechnicianAccountStatus


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
