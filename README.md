# في خدمتك - Backend API

## التشغيل

```bash
# إنشاء البيئة وتفعيلها
python -m venv venv
venv\Scripts\activate   # Windows

# تثبيت المتطلبات
pip install -r requirements.txt

# إنشاء ملف .env (انسخ من .env.example وعدّل DATABASE_URL)
# DATABASE_URL=mysql+pymysql://user:password@localhost:3306/fi_khedmtak

# إنشاء الجداول (إذا كانت قاعدة البيانات فارغة)
python create_tables.py

# إضافة الخدمات الافتراضية
python seed_services.py

# تشغيل السيرفر
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## التوثيق
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## الـ APIs الرئيسية

| المسار | الوصف |
|--------|-------|
| POST /api/auth/send-otp | إرسال رمز التحقق |
| POST /api/auth/verify-otp | التحقق من الرمز |
| POST /api/auth/register/customer | تسجيل عميل |
| POST /api/auth/register/technician | تسجيل فني |
| POST /api/auth/login | تسجيل الدخول |
| GET /api/services | قائمة الخدمات |
| POST /api/requests | إنشاء طلب (يتطلب Token) |
| GET /api/technicians/nearby | أقرب الفنيين وأعلى تقييماً |
