from pydantic import BaseModel


class TechnicianProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    status: str | None = None
    availability_status: str | None = None
    lat: float | None = None
    lng: float | None = None
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
