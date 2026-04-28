from sqlalchemy import inspect, text

from app.database import engine
from app.models.location import District, Governorate


AREA_COLUMNS = {
    "governorate_id": "INT NULL",
    "district_id": "INT NULL",
    "address_details": "VARCHAR(255) NULL",
}


def _has_index(indexes: list[dict], name: str) -> bool:
    return any(index.get("name") == name for index in indexes)


def _has_fk(foreign_keys: list[dict], name: str) -> bool:
    return any(fk.get("name") == name for fk in foreign_keys)


def _add_area_fields(table_name: str) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        print(f"{table_name} table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns(table_name)}
    indexes = inspector.get_indexes(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)

    statements = []
    for column_name, column_type in AREA_COLUMNS.items():
        if column_name not in columns:
            statements.append(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    index_targets = {
        f"ix_{table_name}_governorate_id": "governorate_id",
        f"ix_{table_name}_district_id": "district_id",
    }
    for index_name, column_name in index_targets.items():
        if column_name in columns and not _has_index(indexes, index_name):
            statements.append(f"CREATE INDEX {index_name} ON {table_name} ({column_name})")
        elif column_name not in columns:
            statements.append(f"CREATE INDEX {index_name} ON {table_name} ({column_name})")

    fk_targets = {
        f"fk_{table_name}_governorate_id": (
            "governorate_id",
            "governorates",
            "id",
        ),
        f"fk_{table_name}_district_id": (
            "district_id",
            "districts",
            "id",
        ),
    }
    for fk_name, (column_name, ref_table, ref_column) in fk_targets.items():
        if not _has_fk(foreign_keys, fk_name):
            statements.append(
                f"ALTER TABLE {table_name} "
                f"ADD CONSTRAINT {fk_name} FOREIGN KEY ({column_name}) "
                f"REFERENCES {ref_table}({ref_column})"
            )

    if not statements:
        print(f"{table_name} already has area fields")
        return

    with engine.connect() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Done: {sql}")
            except Exception as exc:
                print(f"Skip: {exc}")


def migrate():
    Governorate.__table__.create(bind=engine, checkfirst=True)
    District.__table__.create(bind=engine, checkfirst=True)
    _add_area_fields("customers")
    _add_area_fields("technicians")


if __name__ == "__main__":
    migrate()
