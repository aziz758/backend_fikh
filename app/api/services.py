from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.service import ServiceResponse
from app.models import Service

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/", response_model=list[ServiceResponse])
def list_services(db: Session = Depends(get_db)):
    return db.query(Service).all()
