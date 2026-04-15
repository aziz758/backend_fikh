from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("technicians"):
        print("technicians table does not exist")
        return

    columns = {col["name"] for col in inspector.get_columns("technicians")}
    migrations = []

    if "service_radius_km" not in columns:
        migrations.append("ALTER TABLE technicians ADD COLUMN service_radius_km FLOAT NULL")
    if "work_start_time" not in columns:
        migrations.append("ALTER TABLE technicians ADD COLUMN work_start_time VARCHAR(5) NULL")
    if "work_end_time" not in columns:
        migrations.append("ALTER TABLE technicians ADD COLUMN work_end_time VARCHAR(5) NULL")
    if "work_days" not in columns:
        migrations.append("ALTER TABLE technicians ADD COLUMN work_days VARCHAR(32) NULL")

    if not migrations:
        print("technicians already has service radius and working hours fields")
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
