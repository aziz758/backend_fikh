from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("request_assignments"):
        print("request_assignments table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("request_assignments")}
    migrations = []

    if "reject_reason" not in columns:
        migrations.append(
            "ALTER TABLE request_assignments ADD COLUMN reject_reason VARCHAR(300) NULL"
        )
    if "rejected_at" not in columns:
        migrations.append(
            "ALTER TABLE request_assignments ADD COLUMN rejected_at DATETIME NULL"
        )

    if not migrations:
        print("request_assignments already has reject fields")
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
