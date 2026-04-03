"""إضافة خدمات افتراضية (كهربائي، سباك، نجار، مهندس)"""
from app.database import SessionLocal
from app.models import Service

SERVICES = ["كهربائي", "سباك", "نجار", "مهندس"]

def seed():
    db = SessionLocal()
    try:
        existing = db.query(Service).count()
        if existing > 0:
            print("الخدمات موجودة مسبقاً")
            return
        for name in SERVICES:
            db.add(Service(name=name))
        db.commit()
        print(f"تم إضافة {len(SERVICES)} خدمات")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
