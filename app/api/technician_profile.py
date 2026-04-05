import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.technician import Technician

router = APIRouter()
UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/status")
def get_profile_status(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["type"] != "technician":
        raise HTTPException(status_code=403, detail="Technicians only")

    tech = db.query(Technician).filter(Technician.id == current_user["id"]).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

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
