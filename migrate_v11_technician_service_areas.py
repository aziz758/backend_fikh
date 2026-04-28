from app.database import engine
from app.models.location import District, Governorate
from app.models.technician import TechnicianServiceArea


def migrate():
    Governorate.__table__.create(bind=engine, checkfirst=True)
    District.__table__.create(bind=engine, checkfirst=True)
    TechnicianServiceArea.__table__.create(bind=engine, checkfirst=True)
    print("Technician service areas table is ready")


if __name__ == "__main__":
    migrate()
