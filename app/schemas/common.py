from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool = True


class MessageResponse(BaseModel):
    message: str
