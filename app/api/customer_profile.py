from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_customer
from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerProfileUpdate, CustomerResponse

router = APIRouter()


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("", response_model=CustomerResponse)
@router.get("/", response_model=CustomerResponse, include_in_schema=False)
@router.get("/me", response_model=CustomerResponse)
@router.get("/me/", response_model=CustomerResponse, include_in_schema=False)
def get_my_profile(
    customer_id: int = Depends(require_customer),
    db: Session = Depends(get_db),
):
    customer = _get_customer_or_404(db, customer_id)
    return customer


@router.put("", response_model=CustomerResponse)
@router.put("/", response_model=CustomerResponse, include_in_schema=False)
@router.put("/me", response_model=CustomerResponse)
@router.put("/me/", response_model=CustomerResponse, include_in_schema=False)
def update_my_profile(
    body: CustomerProfileUpdate,
    customer_id: int = Depends(require_customer),
    db: Session = Depends(get_db),
):
    customer = _get_customer_or_404(db, customer_id)

    if body.name is None and body.lat is None and body.lng is None:
        raise HTTPException(status_code=400, detail="At least one field is required")

    if body.name is not None:
        customer.name = body.name.strip()
    if body.lat is not None:
        customer.lat = body.lat
    if body.lng is not None:
        customer.lng = body.lng

    db.commit()
    db.refresh(customer)
    return customer
