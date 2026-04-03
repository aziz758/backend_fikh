from sqlalchemy import Column, Integer, Boolean, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Review(Base):
    """جدول: يراجع - الفني يراجع الطلب (قبول، تأكيد، حالة الطلب)"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    accepted = Column(Boolean, default=False)
    confirmed = Column(Boolean, default=False)
    status = Column(String(30), nullable=True)  # حالة الطلب من منظور الفني

    technician = relationship("Technician", back_populates="reviews")
    request = relationship("Request", back_populates="reviews")
