from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Governorate(Base):
    __tablename__ = "governorates"

    id = Column(Integer, primary_key=True, index=True)
    name_ar = Column(String(100), nullable=False, unique=True, index=True)
    name_en = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    districts = relationship("District", back_populates="governorate")


class District(Base):
    __tablename__ = "districts"
    __table_args__ = (
        UniqueConstraint("governorate_id", "name_ar", name="uq_district_governorate_name_ar"),
    )

    id = Column(Integer, primary_key=True, index=True)
    governorate_id = Column(Integer, ForeignKey("governorates.id"), nullable=False, index=True)
    name_ar = Column(String(100), nullable=False, index=True)
    name_en = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    governorate = relationship("Governorate", back_populates="districts")
