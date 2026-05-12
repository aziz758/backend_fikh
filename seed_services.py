"""Seed production-like service categories and services."""
from app.database import SessionLocal
from app.models import (
    RequestService,
    Service,
    ServiceCategory,
    TechnicianService,
    TechnicianServiceRequest,
)


SERVICE_CATALOG = [
    (
        "تنظيف",
        [
            "تنظيف منازل",
            "تنظيف شقق بعد التشطيب",
            "تنظيف خزانات المياه",
            "تنظيف سجاد وكنب",
            "تنظيف واجهات زجاجية",
        ],
    ),
    (
        "كهرباء",
        [
            "إصلاح أعطال الكهرباء",
            "تركيب مفاتيح وأفياش",
            "تركيب وصيانة الإنارة",
            "صيانة لوحة الكهرباء",
            "تمديدات كهربائية",
        ],
    ),
    (
        "سباكة",
        [
            "إصلاح تسربات المياه",
            "تسليك المجاري والمغاسل",
            "تركيب خلاطات ومغاسل",
            "صيانة سخانات المياه",
            "تركيب مضخات المياه",
        ],
    ),
    (
        "تكييف",
        [
            "صيانة مكيفات السبليت",
            "تنظيف المكيفات",
            "تعبئة فريون",
            "تركيب مكيف جديد",
            "فحص أعطال التكييف",
        ],
    ),
    (
        "نجارة",
        [
            "إصلاح الأبواب والنوافذ",
            "تركيب أقفال ومفصلات",
            "صيانة المطابخ الخشبية",
            "تركيب رفوف وخزائن",
        ],
    ),
    (
        "دهانات",
        [
            "دهان غرف داخلية",
            "دهان واجهات خارجية",
            "معالجة الرطوبة والتشققات",
            "ترميم جدران",
        ],
    ),
    (
        "أجهزة منزلية",
        [
            "صيانة غسالات",
            "صيانة ثلاجات",
            "صيانة أفران",
            "صيانة شفاطات",
        ],
    ),
    (
        "إنترنت وكاميرات",
        [
            "تركيب كاميرات مراقبة",
            "تمديد شبكات وإنترنت",
            "إعداد راوتر وإنترنت",
            "صيانة أجهزة المراقبة",
        ],
    ),
]

LEGACY_SERVICE_RENAMES = {
    "Electrician": ("كهرباء", "إصلاح أعطال الكهرباء"),
    "Plumber": ("سباكة", "إصلاح تسربات المياه"),
    "Carpenter": ("نجارة", "إصلاح الأبواب والنوافذ"),
    "Engineer": ("إنترنت وكاميرات", "تمديد شبكات وإنترنت"),
    "كهربائي": ("كهرباء", "إصلاح أعطال الكهرباء"),
    "سباك": ("سباكة", "إصلاح تسربات المياه"),
    "نجار": ("نجارة", "إصلاح الأبواب والنوافذ"),
    "مهندس": ("إنترنت وكاميرات", "تمديد شبكات وإنترنت"),
    "تنظيف": ("تنظيف", "تنظيف منازل"),
}


def _get_or_create_category(db, name: str, sort_order: int) -> ServiceCategory:
    category = db.query(ServiceCategory).filter(ServiceCategory.name == name).first()
    if category is None:
        category = ServiceCategory(name=name)
        db.add(category)
        db.flush()
    category.sort_order = sort_order
    category.is_active = True
    return category


def _rename_legacy_services(db, categories_by_name: dict[str, ServiceCategory]) -> None:
    for old_name, (category_name, new_name) in LEGACY_SERVICE_RENAMES.items():
        legacy = db.query(Service).filter(Service.name == old_name).first()
        if legacy is None:
            continue

        existing_new = db.query(Service).filter(Service.name == new_name).first()
        if existing_new is not None and existing_new.id != legacy.id:
            _merge_legacy_service_links(db, legacy, existing_new)
            legacy.is_active = False
            continue

        legacy.name = new_name
        legacy.category_id = categories_by_name[category_name].id
        legacy.is_active = True


def _merge_legacy_service_links(db, legacy: Service, target: Service) -> None:
    technician_links = (
        db.query(TechnicianService)
        .filter(TechnicianService.service_id == legacy.id)
        .all()
    )
    for link in technician_links:
        duplicate = (
            db.query(TechnicianService)
            .filter(
                TechnicianService.technician_id == link.technician_id,
                TechnicianService.service_id == target.id,
                TechnicianService.id != link.id,
            )
            .first()
        )
        if duplicate:
            db.delete(link)
        else:
            link.service_id = target.id

    db.query(RequestService).filter(RequestService.service_id == legacy.id).update(
        {"service_id": target.id},
        synchronize_session=False,
    )
    db.query(TechnicianServiceRequest).filter(
        TechnicianServiceRequest.approved_service_id == legacy.id,
    ).update(
        {"approved_service_id": target.id},
        synchronize_session=False,
    )


def _upsert_service(
    db,
    *,
    name: str,
    category: ServiceCategory,
    sort_order: int,
) -> Service:
    service = db.query(Service).filter(Service.name == name).first()
    if service is None:
        service = Service(name=name)
        db.add(service)
        db.flush()

    service.category_id = category.id
    service.sort_order = sort_order
    service.is_active = True
    return service


def seed():
    db = SessionLocal()
    try:
        categories_by_name = {}
        for category_index, (category_name, _services) in enumerate(SERVICE_CATALOG, start=1):
            category = _get_or_create_category(db, category_name, category_index * 10)
            categories_by_name[category_name] = category

        _rename_legacy_services(db, categories_by_name)

        service_count = 0
        for _category_index, (category_name, services) in enumerate(SERVICE_CATALOG, start=1):
            category = categories_by_name[category_name]
            for service_index, service_name in enumerate(services, start=1):
                _upsert_service(
                    db,
                    name=service_name,
                    category=category,
                    sort_order=service_index * 10,
                )
                service_count += 1

        db.commit()
        print(f"Seeded {len(SERVICE_CATALOG)} service categories")
        print(f"Seeded {service_count} services")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
