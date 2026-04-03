from sqlalchemy import inspect, text

from app.database import SessionLocal, engine
from app.models import Customer, Technician
from app.services.auth_service import hash_password

ADMIN_NAME = "Admin"
ADMIN_PHONE = "0500000000"
ADMIN_PASSWORD = "admin123"


def ensure_is_admin_column() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("customers"):
        raise RuntimeError("customers table does not exist")

    columns = {col["name"] for col in inspector.get_columns("customers")}
    if "is_admin" in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE customers ADD COLUMN is_admin BOOLEAN DEFAULT false"))


def seed_admin() -> None:
    ensure_is_admin_column()

    db = SessionLocal()
    try:
        existing = db.query(Customer).filter(Customer.phone == ADMIN_PHONE).first()
        if existing:
            db.execute(
                text("UPDATE customers SET is_admin = true WHERE id = :id"),
                {"id": existing.id},
            )
            db.commit()
            print(f"Admin already exists: phone={ADMIN_PHONE}")
            return

        phone_taken_by_technician = (
            db.query(Technician).filter(Technician.phone == ADMIN_PHONE).first()
        )
        if phone_taken_by_technician:
            raise RuntimeError(
                f"Cannot create admin, phone {ADMIN_PHONE} already exists in technicians table"
            )

        admin = Customer(
            name=ADMIN_NAME,
            phone=ADMIN_PHONE,
            password_hash=hash_password(ADMIN_PASSWORD),
            status="active",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        db.execute(
            text("UPDATE customers SET is_admin = true WHERE id = :id"),
            {"id": admin.id},
        )
        db.commit()
        print(f"Admin created: phone={ADMIN_PHONE} password={ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
