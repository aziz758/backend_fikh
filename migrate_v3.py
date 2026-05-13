from sqlalchemy import inspect, text

from app.database import engine


def _missing_columns(table_name: str, columns: dict[str, str]) -> list[str]:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        print(f"{table_name} table does not exist")
        return []

    existing = {col["name"] for col in inspector.get_columns(table_name)}
    return [
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        for column_name, column_type in columns.items()
        if column_name not in existing
    ]


def migrate():
    with engine.connect() as conn:
        migrations = []
        migrations.extend(
            _missing_columns(
                "customers",
                {
                    "fcm_token": "VARCHAR(255)",
                },
            )
        )
        migrations.extend(
            _missing_columns(
                "technicians",
                {
                    "fcm_token": "VARCHAR(255)",
                    "availability_status": "VARCHAR(20) DEFAULT 'offline'",
                    "avg_rating": "FLOAT DEFAULT 0.0",
                    "total_ratings": "INT DEFAULT 0",
                    "acceptance_rate": "FLOAT DEFAULT 0.0",
                    "completion_rate": "FLOAT DEFAULT 0.0",
                    "profile_photo_url": "VARCHAR(500)",
                    "id_card_photo_url": "VARCHAR(500)",
                },
            )
        )

        if not migrations:
            print("customers and technicians already have v3 fields")

        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Done: {sql}")
            except Exception as e:
                print(f"Skip: {e}")

        # Backward-compatibility: mirror legacy status into availability status when possible.
        try:
            conn.execute(
                text(
                    "UPDATE technicians "
                    "SET availability_status = status "
                    "WHERE status IN ('available','busy','offline') "
                    "AND (availability_status IS NULL OR availability_status = 'offline')"
                )
            )
            conn.commit()
            print("Synced availability_status from legacy status values")
        except Exception as e:
            print(f"availability sync: {e}")


if __name__ == "__main__":
    migrate()
