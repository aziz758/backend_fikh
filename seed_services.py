"""Seed default services (Electrician, Plumber, Carpenter, Engineer)."""
from app.database import SessionLocal
from app.models import Service

SERVICES = ["Electrician", "Plumber", "Carpenter", "Engineer"]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(Service).count()
        if existing > 0:
            print("Services already exist")
            return
        for name in SERVICES:
            db.add(Service(name=name))
        db.commit()
        print(f"Added {len(SERVICES)} services")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
