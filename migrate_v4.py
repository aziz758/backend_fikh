from app.database import engine
from sqlalchemy import text


def migrate():
    with engine.connect() as conn:
        migrations = [
            "ALTER TABLE requests ADD COLUMN rating_comment TEXT",
            "ALTER TABLE requests ADD COLUMN assigned_at DATETIME",
            "ALTER TABLE requests ADD COLUMN accepted_at DATETIME",
            "ALTER TABLE requests ADD COLUMN completed_at DATETIME",
        ]
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Done: {sql}")
            except Exception as e:
                print(f"Skip: {e}")


if __name__ == "__main__":
    migrate()
