from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    # Integer only (no FK) because user can be in customers or technicians table
    user_id = Column(Integer, nullable=False, index=True)
    user_type = Column(String(20), nullable=False, index=True)  # customer | technician
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
