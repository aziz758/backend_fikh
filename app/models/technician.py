from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TechnicianService(Base):
    """جدول ربط: يحدد - خدمة يقدمها الفني"""
    __tablename__ = "technician_services"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)

    technician = relationship("Technician", back_populates="service_links")


class Technician(Base):
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default="available")  # available, busy, offline
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    # المرتفعات - يمكن أن تكون التخصصات أو التقييم الإجمالي
    specializations = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    service_links = relationship("TechnicianService", back_populates="technician")
    reviews = relationship("Review", back_populates="technician")
    ratings = relationship("Rating", back_populates="technician")
