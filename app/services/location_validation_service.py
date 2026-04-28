from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import District, Governorate


def validate_area_selection(
    db: Session,
    *,
    governorate_id: int | None,
    district_id: int | None,
) -> None:
    if governorate_id is None and district_id is None:
        return
    if governorate_id is None:
        raise HTTPException(
            status_code=400,
            detail="governorate_id is required when district_id is provided",
        )

    governorate = (
        db.query(Governorate)
        .filter(
            Governorate.id == governorate_id,
            Governorate.is_active.is_(True),
        )
        .first()
    )
    if not governorate:
        raise HTTPException(status_code=400, detail="Invalid governorate_id")

    if district_id is None:
        return

    district = (
        db.query(District)
        .filter(
            District.id == district_id,
            District.governorate_id == governorate_id,
            District.is_active.is_(True),
        )
        .first()
    )
    if not district:
        raise HTTPException(status_code=400, detail="Invalid district_id for governorate_id")


def validate_service_area_inputs(db: Session, service_areas) -> None:
    if not service_areas:
        raise HTTPException(status_code=400, detail="At least one service area is required")

    seen: set[tuple[int, int | None]] = set()
    governorate_level: set[int] = set()
    district_level: dict[int, set[int]] = {}

    for area in service_areas:
        governorate_id = int(area.governorate_id)
        district_id = int(area.district_id) if area.district_id is not None else None

        validate_area_selection(
            db,
            governorate_id=governorate_id,
            district_id=district_id,
        )

        key = (governorate_id, district_id)
        if key in seen:
            raise HTTPException(status_code=400, detail="Duplicate service area")
        seen.add(key)

        if district_id is None:
            if district_level.get(governorate_id):
                raise HTTPException(
                    status_code=400,
                    detail="Governorate-level service area overlaps district-level areas",
                )
            governorate_level.add(governorate_id)
            continue

        if governorate_id in governorate_level:
            raise HTTPException(
                status_code=400,
                detail="District-level service area overlaps governorate-level area",
            )
        district_level.setdefault(governorate_id, set()).add(district_id)
