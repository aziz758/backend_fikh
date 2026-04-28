from app.database import Base, engine
from app.models.location import District, Governorate


def migrate():
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Governorate.__table__,
            District.__table__,
        ],
    )
    print("Location tables are ready: governorates, districts")


if __name__ == "__main__":
    migrate()
