from pydantic import BaseModel


class ServiceResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
