from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class RequestAssignment(Base):
    __tablename__ = "request_assignments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, rejected, timeout, cancelled
    timeout_at = Column(DateTime(timezone=True), nullable=True)
    reject_reason = Column(String(300), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
