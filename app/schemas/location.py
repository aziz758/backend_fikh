from pydantic import BaseModel


class GovernorateResponse(BaseModel):
    id: int
    name_ar: str
    name_en: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class DistrictResponse(BaseModel):
    id: int
    governorate_id: int
    name_ar: str
    name_en: str | None = None
    is_active: bool

    class Config:
        from_attributes = True
