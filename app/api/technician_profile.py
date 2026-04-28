from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models import Request as RequestModel, TechnicianServiceArea
from app.models.technician import Technician
from app.schemas.technician_profile import (
    TechnicianAreaUpdateRequest,
    TechnicianAvailabilityUpdateRequest,
    TechnicianAvailabilityUpdateResponse,
    TechnicianDocumentsUploadResponse,
    TechnicianLocationUpdateRequest,
    TechnicianLocationUpdateResponse,
    TechnicianProfileResponse,
    TechnicianProfileStatusResponse,
    TechnicianServiceAreaResponse,
    TechnicianServiceAreasUpdateRequest,
    TechnicianWorkSettingsUpdateRequest,
    TechnicianWorkSettingsUpdateResponse,
)
from app.services.location_validation_service import validate_area_selection, validate_service_area_inputs
from app.services.location_service import (
    is_technician_location_fresh,
    sync_technician_availability_with_location,
)
from app.services.technician_schedule_service import (
    parse_work_days,
    serialize_work_days,
)
from app.services.upload_service import (
    LEGACY_TECHNICIAN_DOCUMENTS_DIR,
    PRIVATE_TECHNICIAN_DOCUMENTS_DIR,
    PUBLIC_TECHNICIAN_PROFILE_UPLOAD_DIR,
    protected_upload_file_response,
    public_upload_url,
    save_validated_image_upload,
)

router = APIRouter()
profile_alias_router = APIRouter(prefix="/profile")
ID_CARD_DOCUMENT_URL = "/api/technician/profile/documents/id-card"


def _get_current_technician(current_user, db: Session) -> Technician:
    if current_user["type"] != "technician":
        raise HTTPException(status_code=403, detail="Technicians only")

    tech = db.query(Technician).filter(Technician.id == current_user["id"]).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech


def _serialize_technician_profile(tech: Technician) -> TechnicianProfileResponse:
    return TechnicianProfileResponse(
        id=tech.id,
        name=tech.name,
        phone=tech.phone,
        status=tech.status,
        availability_status=tech.availability_status,
        lat=tech.lat,
        lng=tech.lng,
        governorate_id=tech.governorate_id,
        governorate_name=tech.governorate.name_ar if tech.governorate else None,
        district_id=tech.district_id,
        district_name=tech.district.name_ar if tech.district else None,
        address_details=tech.address_details,
        location_updated_at=tech.location_updated_at,
        service_radius_km=float(tech.service_radius_km) if tech.service_radius_km is not None else None,
        work_start_time=tech.work_start_time,
        work_end_time=tech.work_end_time,
        work_days=sorted(parse_work_days(tech.work_days)),
        avg_rating=float(tech.avg_rating or 0.0),
        total_ratings=int(tech.total_ratings or 0),
        acceptance_rate=float(tech.acceptance_rate or 0.0),
        completion_rate=float(tech.completion_rate or 0.0),
        profile_photo_url=public_upload_url(tech.profile_photo_url),
        id_card_photo_url=ID_CARD_DOCUMENT_URL if tech.id_card_photo_url else None,
    )


def _serialize_service_area(area: TechnicianServiceArea) -> TechnicianServiceAreaResponse:
    return TechnicianServiceAreaResponse(
        id=area.id,
        governorate_id=area.governorate_id,
        governorate_name=area.governorate.name_ar if area.governorate else None,
        district_id=area.district_id,
        district_name=area.district.name_ar if area.district else None,
        scope="district" if area.district_id is not None else "governorate",
    )


def _list_service_areas_for_technician(db: Session, technician_id: int) -> list[TechnicianServiceAreaResponse]:
    rows = (
        db.query(TechnicianServiceArea)
        .filter(TechnicianServiceArea.technician_id == technician_id)
        .order_by(
            TechnicianServiceArea.governorate_id.asc(),
            TechnicianServiceArea.district_id.asc(),
            TechnicianServiceArea.id.asc(),
        )
        .all()
    )
    return [_serialize_service_area(row) for row in rows]


def _sync_availability_and_commit_if_changed(db: Session, tech: Technician) -> None:
    before = tech.availability_status
    sync_technician_availability_with_location(tech)
    if tech.availability_status != before:
        db.commit()
        db.refresh(tech)


def _update_location_for_current_technician(
    body: TechnicianLocationUpdateRequest,
    current_user,
    db: Session,
) -> Technician:
    tech = _get_current_technician(current_user, db)
    tech.lat = body.lat
    tech.lng = body.lng
    tech.location_updated_at = datetime.utcnow()
    sync_technician_availability_with_location(tech)
    db.commit()
    db.refresh(tech)

    from app.services.firebase_service import (
        sync_request_tracking_realtime,
        sync_technician_realtime,
    )

    sync_technician_realtime(tech)
    active_request = (
        db.query(RequestModel)
        .filter(
            RequestModel.assigned_technician_id == tech.id,
            RequestModel.status == "accepted",
        )
        .order_by(RequestModel.created_at.desc())
        .first()
    )
    if active_request:
        sync_request_tracking_realtime(active_request, tech)

    return tech


def _update_area_for_current_technician(
    body: TechnicianAreaUpdateRequest,
    current_user,
    db: Session,
) -> Technician:
    tech = _get_current_technician(current_user, db)
    provided_fields = body.model_fields_set
    if not provided_fields:
        raise HTTPException(status_code=400, detail="At least one field is required")

    if {"governorate_id", "district_id"} & provided_fields:
        governorate_id = (
            body.governorate_id
            if "governorate_id" in provided_fields
            else tech.governorate_id
        )
        district_id = (
            body.district_id
            if "district_id" in provided_fields
            else tech.district_id
        )
        validate_area_selection(
            db,
            governorate_id=governorate_id,
            district_id=district_id,
        )
        tech.governorate_id = governorate_id
        tech.district_id = district_id

    if "address_details" in provided_fields:
        tech.address_details = body.address_details

    db.commit()
    db.refresh(tech)
    return tech


def _replace_service_areas_for_current_technician(
    body: TechnicianServiceAreasUpdateRequest,
    current_user,
    db: Session,
) -> list[TechnicianServiceAreaResponse]:
    tech = _get_current_technician(current_user, db)
    validate_service_area_inputs(db, body.service_areas)

    db.query(TechnicianServiceArea).filter(
        TechnicianServiceArea.technician_id == tech.id,
    ).delete(synchronize_session=False)

    for area in body.service_areas:
        db.add(
            TechnicianServiceArea(
                technician_id=tech.id,
                governorate_id=area.governorate_id,
                district_id=area.district_id,
            )
        )

    db.commit()
    return _list_service_areas_for_technician(db, tech.id)


def _update_availability_for_current_technician(
    body: TechnicianAvailabilityUpdateRequest,
    current_user,
    db: Session,
) -> Technician:
    tech = _get_current_technician(current_user, db)
    if tech.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved technicians can update availability")
    if tech.availability_status == "busy":
        raise HTTPException(
            status_code=409,
            detail="Cannot change availability while handling an active request",
        )

    if body.availability_status == "on_break":
        tech.availability_status = "on_break"
    elif is_technician_location_fresh(tech):
        tech.availability_status = "available"
    else:
        raise HTTPException(
            status_code=409,
            detail="Live location is required before switching to available",
        )

    db.commit()
    db.refresh(tech)

    from app.services.firebase_service import sync_technician_realtime

    sync_technician_realtime(tech)
    return tech


def _normalize_hhmm(value: str) -> str:
    hour_raw, minute_raw = value.split(":")
    hour = int(hour_raw)
    minute = int(minute_raw)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise HTTPException(status_code=400, detail="Invalid time format, expected HH:MM")
    return f"{hour:02d}:{minute:02d}"


def _update_work_settings_for_current_technician(
    body: TechnicianWorkSettingsUpdateRequest,
    current_user,
    db: Session,
) -> Technician:
    tech = _get_current_technician(current_user, db)
    if tech.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved technicians can update work settings")

    normalized_days = sorted({int(day) for day in body.work_days})
    if any(day < 0 or day > 6 for day in normalized_days):
        raise HTTPException(status_code=400, detail="work_days values must be between 0 and 6")

    tech.service_radius_km = float(body.service_radius_km)
    tech.work_start_time = _normalize_hhmm(body.work_start_time)
    tech.work_end_time = _normalize_hhmm(body.work_end_time)
    tech.work_days = serialize_work_days(normalized_days)

    db.commit()
    db.refresh(tech)

    from app.services.firebase_service import sync_technician_realtime

    sync_technician_realtime(tech)
    return tech


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
@router.get("/me")
@router.get("/me/", include_in_schema=False)
def get_my_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TechnicianProfileResponse:
    tech = _get_current_technician(current_user, db)
    _sync_availability_and_commit_if_changed(db, tech)
    return _serialize_technician_profile(tech)


@router.get("/status", response_model=TechnicianProfileStatusResponse)
def get_profile_status(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    tech = _get_current_technician(current_user, db)
    _sync_availability_and_commit_if_changed(db, tech)
    return {"status": tech.status}


@router.post("/documents", response_model=TechnicianDocumentsUploadResponse)
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

    profile_upload = save_validated_image_upload(
        profile_photo,
        PUBLIC_TECHNICIAN_PROFILE_UPLOAD_DIR,
        public_prefix=f"/{PUBLIC_TECHNICIAN_PROFILE_UPLOAD_DIR}",
    )
    id_upload = save_validated_image_upload(id_card_photo, PRIVATE_TECHNICIAN_DOCUMENTS_DIR)

    tech.profile_photo_url = profile_upload.url
    tech.id_card_photo_url = id_upload.path
    tech.status = "pending_approval"
    db.commit()

    return {"success": True, "status": "pending_approval"}


@router.get("/documents/id-card", include_in_schema=False)
def get_my_id_card_document(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _get_current_technician(current_user, db)
    return protected_upload_file_response(
        tech.id_card_photo_url,
        allowed_dirs=[PRIVATE_TECHNICIAN_DOCUMENTS_DIR, LEGACY_TECHNICIAN_DOCUMENTS_DIR],
    )


@router.put("/location", response_model=TechnicianLocationUpdateResponse)
@router.put("/location/", response_model=TechnicianLocationUpdateResponse, include_in_schema=False)
def update_location(
    body: TechnicianLocationUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_location_for_current_technician(body, current_user, db)
    return {
        "success": True,
        "lat": tech.lat,
        "lng": tech.lng,
        "location_updated_at": tech.location_updated_at,
        "availability_status": tech.availability_status,
    }


@profile_alias_router.put(
    "/location",
    response_model=TechnicianLocationUpdateResponse,
    include_in_schema=False,
)
@profile_alias_router.put(
    "/location/",
    response_model=TechnicianLocationUpdateResponse,
    include_in_schema=False,
)
def update_location_alias(
    body: TechnicianLocationUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_location_for_current_technician(body, current_user, db)
    return {
        "success": True,
        "lat": tech.lat,
        "lng": tech.lng,
        "location_updated_at": tech.location_updated_at,
        "availability_status": tech.availability_status,
    }


@router.put("/area", response_model=TechnicianProfileResponse)
@router.put("/area/", response_model=TechnicianProfileResponse, include_in_schema=False)
def update_area(
    body: TechnicianAreaUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_area_for_current_technician(body, current_user, db)
    return _serialize_technician_profile(tech)


@profile_alias_router.put(
    "/area",
    response_model=TechnicianProfileResponse,
    include_in_schema=False,
)
@profile_alias_router.put(
    "/area/",
    response_model=TechnicianProfileResponse,
    include_in_schema=False,
)
def update_area_alias(
    body: TechnicianAreaUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_area_for_current_technician(body, current_user, db)
    return _serialize_technician_profile(tech)


@router.get("/service-areas", response_model=list[TechnicianServiceAreaResponse])
@router.get(
    "/service-areas/",
    response_model=list[TechnicianServiceAreaResponse],
    include_in_schema=False,
)
def list_service_areas(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _get_current_technician(current_user, db)
    return _list_service_areas_for_technician(db, tech.id)


@router.put("/service-areas", response_model=list[TechnicianServiceAreaResponse])
@router.put(
    "/service-areas/",
    response_model=list[TechnicianServiceAreaResponse],
    include_in_schema=False,
)
def replace_service_areas(
    body: TechnicianServiceAreasUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _replace_service_areas_for_current_technician(body, current_user, db)


@profile_alias_router.get(
    "/service-areas",
    response_model=list[TechnicianServiceAreaResponse],
    include_in_schema=False,
)
@profile_alias_router.get(
    "/service-areas/",
    response_model=list[TechnicianServiceAreaResponse],
    include_in_schema=False,
)
def list_service_areas_alias(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _get_current_technician(current_user, db)
    return _list_service_areas_for_technician(db, tech.id)


@profile_alias_router.put(
    "/service-areas",
    response_model=list[TechnicianServiceAreaResponse],
    include_in_schema=False,
)
@profile_alias_router.put(
    "/service-areas/",
    response_model=list[TechnicianServiceAreaResponse],
    include_in_schema=False,
)
def replace_service_areas_alias(
    body: TechnicianServiceAreasUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _replace_service_areas_for_current_technician(body, current_user, db)


@router.put("/availability", response_model=TechnicianAvailabilityUpdateResponse)
@router.put(
    "/availability/",
    response_model=TechnicianAvailabilityUpdateResponse,
    include_in_schema=False,
)
def update_availability(
    body: TechnicianAvailabilityUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_availability_for_current_technician(body, current_user, db)
    return {"success": True, "availability_status": tech.availability_status or "offline"}


@profile_alias_router.put(
    "/availability",
    response_model=TechnicianAvailabilityUpdateResponse,
    include_in_schema=False,
)
@profile_alias_router.put(
    "/availability/",
    response_model=TechnicianAvailabilityUpdateResponse,
    include_in_schema=False,
)
def update_availability_alias(
    body: TechnicianAvailabilityUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_availability_for_current_technician(body, current_user, db)
    return {"success": True, "availability_status": tech.availability_status or "offline"}


@router.put("/work-settings", response_model=TechnicianWorkSettingsUpdateResponse)
@router.put(
    "/work-settings/",
    response_model=TechnicianWorkSettingsUpdateResponse,
    include_in_schema=False,
)
def update_work_settings(
    body: TechnicianWorkSettingsUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_work_settings_for_current_technician(body, current_user, db)
    return {
        "success": True,
        "service_radius_km": float(tech.service_radius_km or 0.0),
        "work_start_time": tech.work_start_time or "",
        "work_end_time": tech.work_end_time or "",
        "work_days": sorted(parse_work_days(tech.work_days)),
    }


@profile_alias_router.put(
    "/work-settings",
    response_model=TechnicianWorkSettingsUpdateResponse,
    include_in_schema=False,
)
@profile_alias_router.put(
    "/work-settings/",
    response_model=TechnicianWorkSettingsUpdateResponse,
    include_in_schema=False,
)
def update_work_settings_alias(
    body: TechnicianWorkSettingsUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tech = _update_work_settings_for_current_technician(body, current_user, db)
    return {
        "success": True,
        "service_radius_km": float(tech.service_radius_km or 0.0),
        "work_start_time": tech.work_start_time or "",
        "work_end_time": tech.work_end_time or "",
        "work_days": sorted(parse_work_days(tech.work_days)),
    }


@profile_alias_router.get("", include_in_schema=False)
@profile_alias_router.get("/", include_in_schema=False)
@profile_alias_router.get("/me", include_in_schema=False)
@profile_alias_router.get("/me/", include_in_schema=False)
def get_my_profile_alias(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TechnicianProfileResponse:
    tech = _get_current_technician(current_user, db)
    _sync_availability_and_commit_if_changed(db, tech)
    return _serialize_technician_profile(tech)
