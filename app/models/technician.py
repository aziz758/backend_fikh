from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TechnicianService(Base):
    """Link table: maps a technician to services they provide."""

    __tablename__ = "technician_services"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)

    technician = relationship("Technician", back_populates="service_links")


class TechnicianServiceArea(Base):
    """Areas where a technician is willing to provide services."""

    __tablename__ = "technician_service_areas"
    __table_args__ = (
        UniqueConstraint(
            "technician_id",
            "governorate_id",
            "district_id",
            name="uq_technician_service_area",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False, index=True)
    governorate_id = Column(Integer, ForeignKey("governorates.id"), nullable=False, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    technician = relationship("Technician", back_populates="service_areas")
    governorate = relationship("Governorate")
    district = relationship("District")


class TechnicianServiceRequest(Base):
    """Custom service name requested by a technician for admin review."""

    __tablename__ = "technician_service_requests"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False, index=True)
    requested_name = Column(String(150), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    approved_service_id = Column(Integer, ForeignKey("services.id"), nullable=True, index=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    technician = relationship("Technician", back_populates="service_requests")
    approved_service = relationship("Service")


class Technician(Base):
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default="pending_documents")  # pending_documents, pending_approval, approved, rejected
    fcm_token = Column(String(255), nullable=True)
    availability_status = Column(String(20), default="offline")  # available, busy, offline, on_break
    avg_rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    acceptance_rate = Column(Float, default=0.0)
    completion_rate = Column(Float, default=0.0)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    governorate_id = Column(Integer, ForeignKey("governorates.id"), nullable=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True, index=True)
    address_details = Column(String(255), nullable=True)
    location_updated_at = Column(DateTime(timezone=True), nullable=True)
    service_radius_km = Column(Float, nullable=True)
    work_start_time = Column(String(5), nullable=True)  # HH:MM
    work_end_time = Column(String(5), nullable=True)  # HH:MM
    work_days = Column(String(32), nullable=True)  # CSV weekdays, 0=Mon .. 6=Sun
    # Optional profile metadata (specializations or aggregate rating context).
    specializations = Column(String(255), nullable=True)
    profile_photo_url = Column(String(500), nullable=True)
    id_card_photo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    service_links = relationship("TechnicianService", back_populates="technician")
    service_areas = relationship(
        "TechnicianServiceArea",
        back_populates="technician",
        cascade="all, delete-orphan",
    )
    service_requests = relationship(
        "TechnicianServiceRequest",
        back_populates="technician",
        cascade="all, delete-orphan",
    )
    reviews = relationship("Review", back_populates="technician")
    ratings = relationship("Rating", back_populates="technician")
    governorate = relationship("Governorate")
    district = relationship("District")
