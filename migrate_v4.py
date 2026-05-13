from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("requests"):
        print("requests table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("requests")}
    migration_columns = {
        "rating_comment": "TEXT",
        "assigned_at": "DATETIME",
        "accepted_at": "DATETIME",
        "completed_at": "DATETIME",
    }
    migrations = [
        f"ALTER TABLE requests ADD COLUMN {column_name} {column_type}"
        for column_name, column_type in migration_columns.items()
        if column_name not in columns
    ]

    if not migrations:
        print("requests already has v4 fields")
        return

    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Done: {sql}")
            except Exception as e:
                print(f"Skip: {e}")


if __name__ == "__main__":
    migrate()
