import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.technician import Technician

router = APIRouter()
profile_alias_router = APIRouter(prefix="/profile")
UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_current_technician(current_user, db: Session) -> Technician:
    if current_user["type"] != "technician":
        raise HTTPException(status_code=403, detail="Technicians only")

    tech = db.query(Technician).filter(Technician.id == current_user["id"]).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech


def _serialize_technician_profile(tech: Technician) -> dict:
    return {
        "id": tech.id,
        "name": tech.name,
        "phone": tech.phone,
        "status": tech.status,
        "availability_status": tech.availability_status,
        "lat": tech.lat,
        "lng": tech.lng,
        "avg_rating": float(tech.avg_rating or 0.0),
        "total_ratings": int(tech.total_ratings or 0),
        "acceptance_rate": float(tech.acceptance_rate or 0.0),
        "completion_rate": float(tech.completion_rate or 0.0),
        "profile_photo_url": tech.profile_photo_url,
        "id_card_photo_url": tech.id_card_photo_url,
    }


@router.get("")
@router.get("/", include_in_schema=False)
@router.get("/me")
@router.get("/me/", include_in_schema=False)
def get_my_profile(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    tech = _get_current_technician(current_user, db)
    return _serialize_technician_profile(tech)


@router.get("/status")
def get_profile_status(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    tech = _get_current_technician(current_user, db)

    return {"status": tech.status}


@router.post("/documents")
def upload_documents(
    profile_photo: UploadFile = File(...),
    id_card_photo: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["type"] != "technician":
        raise HTTPException(status_code=403, detail="Technicians only")

    tech = db.query(Technician).filter(Technician.id == current_user["id"]).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    profile_ext = (profile_photo.filename or "jpg").split(".")[-1]
    profile_filename = f"{uuid.uuid4()}.{profile_ext}"
    profile_path = os.path.join(UPLOAD_DIR, profile_filename)
    with open(profile_path, "wb") as f:
        shutil.copyfileobj(profile_photo.file, f)

    id_ext = (id_card_photo.filename or "jpg").split(".")[-1]
    id_filename = f"{uuid.uuid4()}.{id_ext}"
    id_path = os.path.join(UPLOAD_DIR, id_filename)
    with open(id_path, "wb") as f:
        shutil.copyfileobj(id_card_photo.file, f)

    tech.profile_photo_url = profile_path
    tech.id_card_photo_url = id_path
    tech.status = "pending_approval"
    db.commit()

    return {"success": True, "status": "pending_approval"}


@router.put("/status")
def update_technician_status(
    body: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["type"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    technician_id = body.get("technician_id")
    new_status = body.get("status")
    if new_status not in ["approved", "rejected", "pending_approval", "pending_documents"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    tech = db.query(Technician).filter(Technician.id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    tech.status = new_status
    db.commit()

    from app.services.firebase_service import notify_user

    if new_status == "approved":
        notify_user(
            db,
            tech.id,
            "technician",
            "Your account has been approved",
            "You can now receive requests",
            "account_approved",
        )
        tech.availability_status = "available"
        db.commit()
    elif new_status == "rejected":
        notify_user(
            db,
            tech.id,
            "technician",
            "Your account was not approved",
            "Please contact support",
            "account_rejected",
        )

    return {"success": True}


@profile_alias_router.get("")
@profile_alias_router.get("/", include_in_schema=False)
@profile_alias_router.get("/me")
@profile_alias_router.get("/me/", include_in_schema=False)
def get_my_profile_alias(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    tech = _get_current_technician(current_user, db)
    return _serialize_technician_profile(tech)
