from sqlalchemy import text

from app.database import engine


def migrate():
    with engine.connect() as conn:
        # customers table
        try:
            conn.execute(text("ALTER TABLE customers ADD COLUMN fcm_token VARCHAR(255)"))
            conn.commit()
            print("Added fcm_token to customers")
        except Exception as e:
            print(f"customers fcm_token: {e}")

        # technicians table
        for col in [
            "ALTER TABLE technicians ADD COLUMN fcm_token VARCHAR(255)",
            "ALTER TABLE technicians ADD COLUMN availability_status VARCHAR(20) DEFAULT 'offline'",
            "ALTER TABLE technicians ADD COLUMN avg_rating FLOAT DEFAULT 0.0",
            "ALTER TABLE technicians ADD COLUMN total_ratings INT DEFAULT 0",
            "ALTER TABLE technicians ADD COLUMN acceptance_rate FLOAT DEFAULT 0.0",
            "ALTER TABLE technicians ADD COLUMN completion_rate FLOAT DEFAULT 0.0",
            "ALTER TABLE technicians ADD COLUMN profile_photo_url VARCHAR(500)",
            "ALTER TABLE technicians ADD COLUMN id_card_photo_url VARCHAR(500)",
        ]:
            try:
                conn.execute(text(col))
                conn.commit()
                print(f"Done: {col}")
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
