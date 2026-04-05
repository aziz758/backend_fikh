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

    # Request location (used by the frontend map flow).
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String(255), nullable=True)

    # Assigned technician and final technician report.
    assigned_technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    technician_report = Column(Text, nullable=True)

    # Customer rating for this request (MVP). Can later move to a dedicated request-linked rating table.
    customer_rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="requests")
    request_services = relationship("RequestService", back_populates="request")
    reviews = relationship("Review", back_populates="request")
    assigned_technician = relationship("Technician")


class RequestService(Base):
    """Link table: one request can include multiple selected services."""

    __tablename__ = "request_services"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    service_type_name = Column(String(100), nullable=True)  # Service type or service name

    request = relationship("Request", back_populates="request_services")
