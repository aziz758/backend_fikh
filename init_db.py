"""
Create the database if it does not exist, then create all tables.
Run: python init_db.py
"""
import pymysql
from sqlalchemy.engine import make_url

from app.config import settings

# Extract connection info from DATABASE_URL
url = make_url(settings.DATABASE_URL)
db_name = url.database
# Connect without selecting a database first so we can create it
connect_args = {
    "host": url.host or "localhost",
    "port": url.port or 3306,
    "user": url.username,
    "password": url.password or "",
    "charset": "utf8mb4",
}


def main():
    conn = pymysql.connect(**connect_args)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print(f"Database is ready: {db_name}")
    finally:
        conn.close()

    # Create tables
    from app.database import engine, Base
    from app import models  # noqa: F401 - register SQLAlchemy models

    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    main()
