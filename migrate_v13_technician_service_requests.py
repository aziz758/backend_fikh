from app.database import engine
from app.models.service import Service
from app.models.technician import Technician, TechnicianServiceRequest


def migrate():
    Technician.__table__.create(bind=engine, checkfirst=True)
    Service.__table__.create(bind=engine, checkfirst=True)
    TechnicianServiceRequest.__table__.create(bind=engine, checkfirst=True)
    print("Technician service requests table is ready")


if __name__ == "__main__":
    migrate()
