from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), default="active")  # active, inactive
    fcm_token = Column(String(255), nullable=True)
    profile_photo_url = Column(String(500), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    governorate_id = Column(Integer, ForeignKey("governorates.id"), nullable=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True, index=True)
    address_details = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    requests = relationship("Request", back_populates="customer")
    ratings = relationship("Rating", back_populates="customer")
    governorate = relationship("Governorate")
    district = relationship("District")
