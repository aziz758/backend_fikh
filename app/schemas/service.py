from pydantic import BaseModel


class ServiceResponse(BaseModel):
    id: int
    name: str
    category_id: int | None = None
    category_name: str | None = None
    sort_order: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class ServiceCategoryResponse(BaseModel):
    id: int
    name: str
    sort_order: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class ServiceGroupResponse(BaseModel):
    id: int | None = None
    name: str
    sort_order: int = 0
    services: list[ServiceResponse]
