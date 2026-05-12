from sqlalchemy import inspect, text

from app.database import engine


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("services"):
        print("services table does not exist")
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS service_categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    sort_order INT NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT true
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        )
        print("service_categories table is ready")

    service_columns = _column_names("services")
    migrations = []
    if "category_id" not in service_columns:
        migrations.append("ALTER TABLE services ADD COLUMN category_id INT NULL")
    if "sort_order" not in service_columns:
        migrations.append("ALTER TABLE services ADD COLUMN sort_order INT NOT NULL DEFAULT 0")
    if "is_active" not in service_columns:
        migrations.append("ALTER TABLE services ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true")

    with engine.begin() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                print(f"Done: {sql}")
            except Exception as exc:
                print(f"Skip: {exc}")

    inspector = inspect(engine)
    indexes = {idx["name"] for idx in inspector.get_indexes("services")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("services") if fk.get("name")}

    with engine.begin() as conn:
        if "ix_services_category_id" not in indexes:
            try:
                conn.execute(text("CREATE INDEX ix_services_category_id ON services (category_id)"))
                print("Added ix_services_category_id")
            except Exception as exc:
                print(f"Skip index: {exc}")

        if "fk_services_category_id" not in foreign_keys:
            try:
                conn.execute(
                    text(
                        """
                        ALTER TABLE services
                        ADD CONSTRAINT fk_services_category_id
                        FOREIGN KEY (category_id) REFERENCES service_categories(id)
                        """
                    )
                )
                print("Added fk_services_category_id")
            except Exception as exc:
                print(f"Skip foreign key: {exc}")


if __name__ == "__main__":
    migrate()
