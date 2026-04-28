from sqlalchemy import inspect, text

from app.database import engine
from app.models.location import District, Governorate


def _has_index(indexes: list[dict], name: str) -> bool:
    return any(index.get("name") == name for index in indexes)


def _has_fk(foreign_keys: list[dict], name: str) -> bool:
    return any(fk.get("name") == name for fk in foreign_keys)


def _run_statements(statements: list[str]) -> None:
    with engine.connect() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Done: {sql}")
            except Exception as exc:
                print(f"Skip: {exc}")


def _add_request_area_fields() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("requests"):
        print("requests table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("requests")}
    indexes = inspector.get_indexes("requests")
    foreign_keys = inspector.get_foreign_keys("requests")

    statements = []
    if "governorate_id" not in columns:
        statements.append("ALTER TABLE requests ADD COLUMN governorate_id INT NULL")
    if "district_id" not in columns:
        statements.append("ALTER TABLE requests ADD COLUMN district_id INT NULL")

    if not _has_index(indexes, "ix_requests_governorate_id"):
        statements.append("CREATE INDEX ix_requests_governorate_id ON requests (governorate_id)")
    if not _has_index(indexes, "ix_requests_district_id"):
        statements.append("CREATE INDEX ix_requests_district_id ON requests (district_id)")

    if not _has_fk(foreign_keys, "fk_requests_governorate_id"):
        statements.append(
            "ALTER TABLE requests "
            "ADD CONSTRAINT fk_requests_governorate_id "
            "FOREIGN KEY (governorate_id) REFERENCES governorates(id)"
        )
    if not _has_fk(foreign_keys, "fk_requests_district_id"):
        statements.append(
            "ALTER TABLE requests "
            "ADD CONSTRAINT fk_requests_district_id "
            "FOREIGN KEY (district_id) REFERENCES districts(id)"
        )

    if not statements:
        print("requests already has area fields")
        return
    _run_statements(statements)


def _add_rating_request_link() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("ratings"):
        print("ratings table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("ratings")}
    indexes = inspector.get_indexes("ratings")
    foreign_keys = inspector.get_foreign_keys("ratings")

    statements = []
    if "request_id" not in columns:
        statements.append("ALTER TABLE ratings ADD COLUMN request_id INT NULL")

    if not _has_index(indexes, "ix_ratings_request_id"):
        statements.append("CREATE INDEX ix_ratings_request_id ON ratings (request_id)")
    if not _has_index(indexes, "uq_ratings_request_id"):
        statements.append("CREATE UNIQUE INDEX uq_ratings_request_id ON ratings (request_id)")

    if not _has_fk(foreign_keys, "fk_ratings_request_id"):
        statements.append(
            "ALTER TABLE ratings "
            "ADD CONSTRAINT fk_ratings_request_id "
            "FOREIGN KEY (request_id) REFERENCES requests(id)"
        )

    if not statements:
        print("ratings already has request link")
        return
    _run_statements(statements)


def migrate():
    Governorate.__table__.create(bind=engine, checkfirst=True)
    District.__table__.create(bind=engine, checkfirst=True)
    _add_request_area_fields()
    _add_rating_request_link()


if __name__ == "__main__":
    migrate()
