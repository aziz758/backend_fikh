from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    note = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    status = Column(String(30), default="pending")  # pending, assigned, accepted, completed, cancelled

    # موقع الطلب (للربط مع الفرونت)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String(255), nullable=True)

    # إسناد الطلب لفني + تقريره
    assigned_technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    technician_report = Column(Text, nullable=True)

    # تقييم العميل للطلب (MVP). يمكن لاحقاً نقله لجدول rating مرتبط بالطلب
    customer_rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="requests")
    request_services = relationship("RequestService", back_populates="request")
    reviews = relationship("Review", back_populates="request")
    assigned_technician = relationship("Technician")


class RequestService(Base):
    """جدول ربط: يختار - طلب واحد يمكن أن يختار عدة خدمات"""
    __tablename__ = "request_services"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    service_type_name = Column(String(100), nullable=True)  # نوع او اسم الخدمة

    request = relationship("Request", back_populates="request_services")
