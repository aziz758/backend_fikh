from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.service import ServiceGroupResponse, ServiceResponse
from app.models import Service, ServiceCategory

router = APIRouter(prefix="/services", tags=["services"])


def _serialize_service(service: Service) -> dict:
    category = service.category
    return {
        "id": service.id,
        "name": service.name,
        "category_id": service.category_id,
        "category_name": category.name if category else None,
        "sort_order": int(service.sort_order or 0),
        "is_active": bool(service.is_active),
    }


@router.get("/grouped", response_model=list[ServiceGroupResponse])
def list_services_grouped(db: Session = Depends(get_db)):
    categories = (
        db.query(ServiceCategory)
        .filter(ServiceCategory.is_active.is_(True))
        .order_by(ServiceCategory.sort_order.asc(), ServiceCategory.name.asc())
        .all()
    )
    services = (
        db.query(Service)
        .filter(Service.is_active.is_(True))
        .order_by(Service.sort_order.asc(), Service.name.asc())
        .all()
    )

    services_by_category: dict[int | None, list[Service]] = {}
    for service in services:
        services_by_category.setdefault(service.category_id, []).append(service)

    groups: list[dict] = []
    for category in categories:
        category_services = services_by_category.pop(category.id, [])
        if not category_services:
            continue
        groups.append(
            {
                "id": category.id,
                "name": category.name,
                "sort_order": int(category.sort_order or 0),
                "services": [_serialize_service(service) for service in category_services],
            }
        )

    uncategorized_services = services_by_category.pop(None, [])
    if uncategorized_services:
        groups.append(
            {
                "id": None,
                "name": "خدمات أخرى",
                "sort_order": 9999,
                "services": [_serialize_service(service) for service in uncategorized_services],
            }
        )

    return groups


@router.get("/", response_model=list[ServiceResponse])
def list_services(db: Session = Depends(get_db)):
    services = (
        db.query(Service)
        .outerjoin(ServiceCategory, Service.category_id == ServiceCategory.id)
        .filter(Service.is_active.is_(True))
        .order_by(
            ServiceCategory.sort_order.asc(),
            Service.sort_order.asc(),
            Service.name.asc(),
        )
        .all()
    )
    return [_serialize_service(service) for service in services]
