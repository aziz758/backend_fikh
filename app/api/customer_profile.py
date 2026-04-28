from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_customer
from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerProfileUpdate, CustomerResponse
from app.services.location_validation_service import validate_area_selection

router = APIRouter()


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _serialize_customer_profile(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "status": customer.status,
        "lat": customer.lat,
        "lng": customer.lng,
        "governorate_id": customer.governorate_id,
        "governorate_name": customer.governorate.name_ar if customer.governorate else None,
        "district_id": customer.district_id,
        "district_name": customer.district.name_ar if customer.district else None,
        "address_details": customer.address_details,
        "created_at": customer.created_at,
    }


@router.get("", response_model=CustomerResponse, include_in_schema=False)
@router.get("/", response_model=CustomerResponse, include_in_schema=False)
@router.get("/me", response_model=CustomerResponse)
@router.get("/me/", response_model=CustomerResponse, include_in_schema=False)
def get_my_profile(
    customer_id: int = Depends(require_customer),
    db: Session = Depends(get_db),
):
    customer = _get_customer_or_404(db, customer_id)
    return _serialize_customer_profile(customer)


@router.put("", response_model=CustomerResponse, include_in_schema=False)
@router.put("/", response_model=CustomerResponse, include_in_schema=False)
@router.put("/me", response_model=CustomerResponse)
@router.put("/me/", response_model=CustomerResponse, include_in_schema=False)
def update_my_profile(
    body: CustomerProfileUpdate,
    customer_id: int = Depends(require_customer),
    db: Session = Depends(get_db),
):
    customer = _get_customer_or_404(db, customer_id)
    provided_fields = body.model_fields_set

    if not provided_fields:
        raise HTTPException(status_code=400, detail="At least one field is required")

    if "name" in provided_fields and body.name is not None:
        customer.name = body.name.strip()
    if "lat" in provided_fields:
        customer.lat = body.lat
    if "lng" in provided_fields:
        customer.lng = body.lng
    if {"governorate_id", "district_id"} & provided_fields:
        governorate_id = (
            body.governorate_id
            if "governorate_id" in provided_fields
            else customer.governorate_id
        )
        district_id = (
            body.district_id
            if "district_id" in provided_fields
            else customer.district_id
        )
        validate_area_selection(
            db,
            governorate_id=governorate_id,
            district_id=district_id,
        )
        customer.governorate_id = governorate_id
        customer.district_id = district_id
    if "address_details" in provided_fields:
        customer.address_details = body.address_details

    db.commit()
    db.refresh(customer)
    return _serialize_customer_profile(customer)
