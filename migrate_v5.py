from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("technicians"):
        print("technicians table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("technicians")}
    if "location_updated_at" in columns:
        print("location_updated_at already exists")
        return

    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE technicians ADD COLUMN location_updated_at DATETIME NULL"))
            conn.commit()
            print("Added location_updated_at to technicians")
        except Exception as e:
            print(f"Migration failed: {e}")


if __name__ == "__main__":
    migrate()
