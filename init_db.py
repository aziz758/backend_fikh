"""
إنشاء قاعدة البيانات إذا لم تكن موجودة، ثم إنشاء الجداول.
شغّل: python init_db.py
"""
import pymysql
from sqlalchemy.engine import make_url

from app.config import settings

# استخراج بيانات الاتصال من DATABASE_URL
url = make_url(settings.DATABASE_URL)
db_name = url.database
# الاتصال بدون تحديد قاعدة البيانات لإنشائها
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
        print(f"تم التأكد من وجود قاعدة البيانات: {db_name}")
    finally:
        conn.close()

    # إنشاء الجداول
    from app.database import engine, Base
    from app import models  # noqa: F401 - لتسجيل النماذج
    Base.metadata.create_all(bind=engine)
    print("تم إنشاء الجداول.")

if __name__ == "__main__":
    main()
