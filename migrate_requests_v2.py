"""
Migration helper (بدون Alembic):
- يضيف أعمدة جديدة لجدول requests إذا كانت غير موجودة.

شغّل:
  python migrate_requests_v2.py
"""

from sqlalchemy import inspect, text

from app.database import engine


def _has_column(columns: list[dict], name: str) -> bool:
    return any(c.get("name") == name for c in columns)


def main() -> None:
    insp = inspect(engine)
    if not insp.has_table("requests"):
        print("جدول requests غير موجود. شغّل create_tables.py أولاً أو init_db.py.")
        return

    cols = insp.get_columns("requests")
    alters: list[str] = []

    # Location fields
    if not _has_column(cols, "lat"):
        alters.append("ADD COLUMN lat DOUBLE NULL")
    if not _has_column(cols, "lng"):
        alters.append("ADD COLUMN lng DOUBLE NULL")
    if not _has_column(cols, "address"):
        alters.append("ADD COLUMN address VARCHAR(255) NULL")

    # Assignment / workflow
    if not _has_column(cols, "assigned_technician_id"):
        alters.append("ADD COLUMN assigned_technician_id INT NULL")
    if not _has_column(cols, "technician_report"):
        alters.append("ADD COLUMN technician_report TEXT NULL")
    if not _has_column(cols, "customer_rating"):
        alters.append("ADD COLUMN customer_rating DOUBLE NULL")

    if not alters:
        print("لا توجد تغييرات مطلوبة: الأعمدة موجودة مسبقاً.")
        return

    stmt = "ALTER TABLE requests " + ", ".join(alters)
    with engine.begin() as conn:
        conn.execute(text(stmt))

    print("تم تحديث جدول requests بنجاح.")


if __name__ == "__main__":
    main()

