from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import District, Governorate
from app.schemas.location import DistrictResponse, GovernorateResponse

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/governorates", response_model=list[GovernorateResponse])
def list_governorates(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = db.query(Governorate)
    if not include_inactive:
        query = query.filter(Governorate.is_active.is_(True))
    return query.order_by(Governorate.name_ar.asc()).all()


@router.get("/districts", response_model=list[DistrictResponse])
def list_districts(
    governorate_id: int = Query(..., gt=0),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    governorate_query = db.query(Governorate).filter(Governorate.id == governorate_id)
    if not include_inactive:
        governorate_query = governorate_query.filter(Governorate.is_active.is_(True))
    governorate = governorate_query.first()
    if not governorate:
        raise HTTPException(status_code=404, detail="Governorate not found")

    query = db.query(District).filter(District.governorate_id == governorate_id)
    if not include_inactive:
        query = query.filter(District.is_active.is_(True))
    return query.order_by(District.name_ar.asc()).all()
