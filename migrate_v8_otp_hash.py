from sqlalchemy import inspect, text

from app.database import engine


def migrate():
    inspector = inspect(engine)
    if not inspector.has_table("otp_verifications"):
        print("otp_verifications table does not exist")
        return

    columns = {col["name"]: col for col in inspector.get_columns("otp_verifications")}
    code_column = columns.get("code")
    if not code_column:
        print("otp_verifications.code column does not exist")
        return

    current_length = getattr(code_column.get("type"), "length", None)
    if current_length is not None and int(current_length) >= 64:
        print("otp_verifications.code is already large enough")
        return

    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE otp_verifications MODIFY COLUMN code VARCHAR(64) NOT NULL"))
            conn.commit()
            print("Expanded otp_verifications.code to VARCHAR(64)")
        except Exception as e:
            print(f"Migration failed: {e}")


if __name__ == "__main__":
    migrate()
