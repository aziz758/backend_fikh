from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("customers"):
        print("customers table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("customers")}
    if "profile_photo_url" in columns:
        print("customers.profile_photo_url already exists")
        return

    with engine.connect() as conn:
        try:
            conn.execute(
                text("ALTER TABLE customers ADD COLUMN profile_photo_url VARCHAR(500) NULL")
            )
            conn.commit()
            print("Added profile_photo_url to customers")
        except Exception as exc:
            print(f"Migration failed: {exc}")


if __name__ == "__main__":
    migrate()
