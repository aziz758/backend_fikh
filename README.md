
# Fi Khedmtak Backend API

## 1. Project Overview
### العربية
هذا المشروع هو **Backend API** مبني بـ FastAPI لتطبيق خدمات ميدانية يربط العميل بالفني. النظام يدعم:
- التسجيل وتسجيل الدخول والتحقق عبر OTP.
- إنشاء طلبات الخدمة وإسنادها لفني تلقائياً.
- قبول الطلب وإنجازه وتقييم الفني.
- إشعارات داخل التطبيق + إشعارات Push عبر Firebase (FCM).
- رفع مستندات الفني ومراجعة حالة حسابه.

**أنواع المستخدمين (3 أدوار):**
| نوع المستخدم | الدور | حالة التنفيذ الحالية |
|---|---|---|
| `customer` | ينشئ الطلبات، يتابعها، ويقيّم الفني | مكتمل في الـ API |
| `technician` | يستقبل الطلبات، يقبلها، ينفذها، ويرفع مستنداته | مكتمل في الـ API |
| `admin` | يغيّر حالة الفني (قبول/رفض/مراجعة) | مدعوم جزئياً (تحقق نوع المستخدم فقط، بدون نموذج/Admin panel كامل) |

### English
This project is a **FastAPI backend** for an on-demand field service platform that connects customers with technicians. It supports:
- OTP-based auth, registration, and login.
- Service request creation with automatic technician assignment.
- Request acceptance, completion, and rating.
- In-app notifications + Firebase FCM push notifications.
- Technician document upload and account status review.

**3 user types and roles:**
| User Type | Role | Current Implementation Status |
|---|---|---|
| `customer` | Creates requests, tracks them, and rates technicians | Fully implemented in API |
| `technician` | Receives, accepts, and completes requests; uploads documents | Fully implemented in API |
| `admin` | Updates technician account status | Partially implemented (user type check only, no full admin model/panel) |

---

## 2. Tech Stack
### العربية
| المكتبة | لماذا مستخدمة |
|---|---|
| `fastapi` | بناء REST API وتعريف المسارات والاعتمادات (Depends) |
| `uvicorn[standard]` | تشغيل تطبيق ASGI (FastAPI) محلياً وفي التطوير |
| `sqlalchemy` | ORM وتعريف الجداول والنماذج والاستعلامات |
| `pymysql` | Driver للاتصال بـ MySQL من SQLAlchemy |
| `python-jose[cryptography]` | إنشاء/فك JWT tokens |
| `passlib[bcrypt]` | تشفير كلمات المرور والتحقق منها |
| `bcrypt` | خوارزمية التجزئة المستخدمة مع Passlib |
| `cryptography` | دعم أمني مطلوب لمكونات JWT/Bcrypt/Firebase |
| `python-multipart` | دعم استقبال ملفات `multipart/form-data` (رفع مستندات الفني) |
| `httpx` | HTTP client غير متزامن لإرسال OTP عبر مزود SMS |
| `python-dotenv` | تحميل متغيرات البيئة من ملف `.env` |
| `pydantic-settings` | موجود ضمن المتطلبات (حالياً الإعدادات تُقرأ يدوياً عبر `os.getenv`) |
| `firebase-admin` | إرسال إشعارات Push عبر FCM باستخدام Service Account |

### English
| Library | Why It Is Used |
|---|---|
| `fastapi` | REST API framework, routing, dependency injection |
| `uvicorn[standard]` | ASGI server to run FastAPI |
| `sqlalchemy` | ORM, models, relations, and DB queries |
| `pymysql` | MySQL driver for SQLAlchemy |
| `python-jose[cryptography]` | JWT creation and decoding |
| `passlib[bcrypt]` | Password hashing and verification |
| `bcrypt` | Hashing algorithm backend for password security |
| `cryptography` | Security primitives used by auth/dependency chain |
| `python-multipart` | Multipart/form-data support for file uploads |
| `httpx` | Async HTTP client (SMS OTP provider requests) |
| `python-dotenv` | Loads environment variables from `.env` |
| `pydantic-settings` | Installed in requirements (not directly used in current settings class) |
| `firebase-admin` | Firebase Admin SDK for FCM push notifications |

---

## 3. Project Structure
### العربية
**ملاحظة:** هذا القسم يوثق كل المجلدات وكل الملفات الموجودة حالياً داخل المشروع (مع استثناء `venv` حسب طلبك). ملفات `__pycache__` ملفات مولدة تلقائياً من بايثون.

#### المجلدات
| المسار | الوصف (AR) | Description (EN) |
|---|---|---|
| `app/` | الحزمة الأساسية للتطبيق | Main application package |
| `app/api/` | جميع راوترات الـ API | All API routers |
| `app/models/` | نماذج SQLAlchemy للجداول | SQLAlchemy table models |
| `app/schemas/` | نماذج Pydantic للمدخلات/المخرجات | Pydantic request/response schemas |
| `app/services/` | منطق الأعمال والخدمات (Auth/SMS/FCM/Assignment) | Business service layer |
| `uploads/` | مجلد حفظ الملفات المرفوعة | Upload storage root |
| `uploads/documents/` | ملفات مستندات الفنيين | Technician document uploads |
| `__pycache__/` | كاش bytecode على مستوى الجذر | Root-level Python bytecode cache |
| `app/__pycache__/` | كاش bytecode لملفات `app` | Bytecode cache for `app` |
| `app/api/__pycache__/` | كاش bytecode لراوترات API | Bytecode cache for API modules |
| `app/models/__pycache__/` | كاش bytecode للنماذج | Bytecode cache for models |
| `app/schemas/__pycache__/` | كاش bytecode للـ schemas | Bytecode cache for schemas |
| `app/services/__pycache__/` | كاش bytecode للخدمات | Bytecode cache for services |

#### الملفات المصدرية/الإعدادية (غير الكاش)
| الملف | الوصف (AR) | Description (EN) |
|---|---|---|
| `.env` | إعدادات التشغيل المحلية (حاليًا يحتوي متغيرات DB/JWT/SMS) | Local runtime environment variables |
| `.env.example` | قالب متغيرات البيئة للمشروع | Example environment template |
| `README.md` | توثيق المشروع | Project documentation |
| `requirements.txt` | كل مكتبات بايثون المطلوبة | Python dependencies list |
| `main.py` | إنشاء تطبيق FastAPI وتسجيل جميع الراوترات | FastAPI app entrypoint and router registration |
| `create_tables.py` | إنشاء كل الجداول عبر `Base.metadata.create_all` | Create all DB tables from models |
| `init_db.py` | إنشاء قاعدة البيانات (إن لم تكن موجودة) ثم إنشاء الجداول | Create DB if missing, then create tables |
| `migrate_requests_v2.py` | Migration لإضافة أعمدة إضافية في جدول `requests` | Migration helper for request columns |
| `migrate_v3.py` | Migration لإضافة أعمدة FCM/إحصائيات الفني + أعمدة صور المستندات | Migration helper for v3 columns |
| `seed_services.py` | Seed بيانات الخدمات الافتراضية | Seed default services |
| `firebase_credentials.json` | ملف Firebase Service Account (مفاتيح الاعتماد) | Firebase service account credential file |
| `app/__init__.py` | تعريف حزمة `app` | `app` package initializer |
| `app/config.py` | تحميل `.env` وبناء كائن `settings` | Environment loading and settings object |
| `app/database.py` | إعداد `engine` و`SessionLocal` و`Base` و`get_db` | SQLAlchemy engine/session/base setup |
| `app/api/__init__.py` | تعريف حزمة راوترات API | API package initializer |
| `app/api/dependencies.py` | JWT auth dependencies (`get_current_user*`, role guards) | Auth dependencies and role guards |
| `app/api/auth.py` | جميع مسارات المصادقة وكلمة المرور وFCM token update | Auth and credential endpoints |
| `app/api/services.py` | مسار جلب الخدمات | Service listing endpoint |
| `app/api/technicians.py` | مسار البحث عن الفنيين القريبين | Nearby technicians endpoint |
| `app/api/requests.py` | مسارات دورة حياة الطلب (إنشاء/قبول/إكمال/تقييم) | Request lifecycle endpoints |
| `app/api/notifications.py` | مسارات الإشعارات (عرض/قراءة/حذف) | Notification CRUD-like endpoints |
| `app/api/technician_profile.py` | مسارات حالة الفني ورفع المستندات وتغيير الحالة من admin | Technician profile/document/status endpoints |
| `app/models/__init__.py` | تجميع وتصدير كل النماذج | Model exports registry |
| `app/models/customer.py` | نموذج جدول العملاء | Customer table model |
| `app/models/technician.py` | نموذج الفني + جدول الربط `technician_services` | Technician and technician-services link models |
| `app/models/service.py` | نموذج جدول الخدمات | Service table model |
| `app/models/request.py` | نموذج الطلب + جدول الربط `request_services` | Request and request-services link models |
| `app/models/review.py` | نموذج جدول مراجعات الفني للطلبات | Review table model |
| `app/models/rating.py` | نموذج جدول تقييمات العملاء للفنيين | Rating table model |
| `app/models/otp.py` | نموذج OTP verification | OTP verification table model |
| `app/models/notification.py` | نموذج الإشعارات داخل النظام | Notification table model |
| `app/models/request_assignment.py` | نموذج تعيين الفنيين للطلبات مع timeout/status | Request assignment table model |
| `app/schemas/__init__.py` | تعريف حزمة schemas | Schemas package initializer |
| `app/schemas/auth.py` | Schemas لطلبات auth/OTP/login/password | Auth request/response schemas |
| `app/schemas/customer.py` | Schemas للعميل | Customer schemas |
| `app/schemas/technician.py` | Schemas للفني | Technician schemas |
| `app/schemas/service.py` | Schema استجابة الخدمات | Service response schema |
| `app/schemas/request_schema.py` | Schemas إنشاء/استجابة الطلب | Request schemas |
| `app/services/__init__.py` | تعريف حزمة الخدمات | Services package initializer |
| `app/services/auth_service.py` | JWT + password hashing + OTP business logic | Auth/OTP core logic |
| `app/services/sms_service.py` | إرسال OTP عبر HTTP provider أو وضع dev | OTP SMS transport layer |
| `app/services/firebase_service.py` | Firebase init + push + حفظ إشعار DB | FCM + notification persistence service |
| `app/services/assignment_service.py` | اختيار الفني + timeout + إعادة الإسناد | Assignment scoring and timeout engine |

<details>
<summary><strong>Generated Cache Files (كل ملفات الكاش الحالية)</strong></summary>

| الملف | الوصف (AR) | Description (EN) |
|---|---|---|
| `__pycache__/create_tables.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `__pycache__/init_db.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `__pycache__/main.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `__pycache__/main.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `__pycache__/migrate_requests_v2.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `__pycache__/migrate_v3.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `__pycache__/seed_services.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/__pycache__/__init__.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/__pycache__/__init__.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/__pycache__/__init__.cpython-312.pyc.2560328634800` | ملف كاش إضافي مولد تلقائياً | Auto-generated cache variant |
| `app/__pycache__/config.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/__pycache__/config.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/__pycache__/database.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/__pycache__/database.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/__init__.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/__init__.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/__init__.cpython-312.pyc.2560332006448` | ملف كاش إضافي مولد تلقائياً | Auto-generated cache variant |
| `app/api/__pycache__/auth.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/auth.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/auth.cpython-312.pyc.2560328636928` | ملف كاش إضافي مولد تلقائياً | Auto-generated cache variant |
| `app/api/__pycache__/dependencies.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/dependencies.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/notifications.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/notifications.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/requests.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/requests.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/services.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/services.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/technician_profile.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/technician_profile.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/technicians.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/api/__pycache__/technicians.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/__init__.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/__init__.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/customer.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/customer.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/notification.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/notification.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/otp.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/otp.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/rating.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/rating.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/request.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/request.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/request_assignment.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/request_assignment.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/review.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/review.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/service.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/service.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/technician.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/models/__pycache__/technician.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/__init__.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/__init__.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/auth.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/auth.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/customer.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/customer.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/request_schema.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/request_schema.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/service.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/service.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/technician.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/schemas/__pycache__/technician.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/__init__.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/__init__.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/assignment_service.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/assignment_service.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/auth_service.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/auth_service.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/firebase_service.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/firebase_service.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/sms_service.cpython-311.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |
| `app/services/__pycache__/sms_service.cpython-312.pyc` | ملف bytecode مولد تلقائياً | Auto-generated Python bytecode cache |

</details>

### English
The full project tree above is bilingual (`AR + EN`) and includes:
- All source/config files.
- All runtime-generated cache files currently present.
- All folders except `venv` (excluded by request).

---

## 4. Database Tables
### العربية
> قاعدة البيانات تعتمد على SQLAlchemy models. الجداول التالية معرفة في `app/models`.

### `customers`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف العميل |
| `name` | String(100) | اسم العميل |
| `phone` | String(20), unique, indexed | رقم الهاتف (هوية تسجيل) |
| `password_hash` | String(255) | كلمة مرور مشفرة |
| `status` | String(20), default `active` | حالة العميل |
| `fcm_token` | String(255), nullable | FCM token لإشعارات الموبايل |
| `lat` / `lng` | Float, nullable | آخر موقع معروف |
| `created_at` | DateTime, server default now | وقت الإنشاء |

### `technicians`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف الفني |
| `name` | String(100) | اسم الفني |
| `phone` | String(20), unique, indexed | رقم الهاتف |
| `password_hash` | String(255) | كلمة مرور مشفرة |
| `status` | String(20), default `available` | حالة حساب/حقل legacy مستخدم أيضاً في الفلاتر |
| `fcm_token` | String(255), nullable | FCM token للفني |
| `availability_status` | String(20), default `offline` | حالة التوفر التشغيلية (`available/busy/offline`) |
| `avg_rating` | Float, default `0.0` | متوسط التقييم المخزن |
| `total_ratings` | Integer, default `0` | عدد التقييمات |
| `acceptance_rate` | Float, default `0.0` | معدل قبول الطلبات |
| `completion_rate` | Float, default `0.0` | معدل إكمال الطلبات |
| `lat` / `lng` | Float, nullable | موقع الفني |
| `specializations` | String(255), nullable | وصف/تخصصات إضافية |
| `profile_photo_url` | String(500), nullable | مسار صورة الملف الشخصي |
| `id_card_photo_url` | String(500), nullable | مسار صورة الهوية |
| `created_at` | DateTime, server default now | وقت إنشاء الحساب |

### `technician_services`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف السجل |
| `technician_id` | Integer FK -> technicians.id | الفني |
| `service_id` | Integer FK -> services.id | الخدمة التي يقدمها الفني |

### `services`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف الخدمة |
| `name` | String(100) | اسم الخدمة |

### `requests`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف الطلب |
| `customer_id` | Integer FK -> customers.id | صاحب الطلب |
| `note` | Text, nullable | وصف إضافي |
| `image_url` | String(500), nullable | رابط/مسار صورة |
| `status` | String(30), default `pending` | حالة الطلب (`pending/assigned/accepted/completed/cancelled`) |
| `lat` / `lng` | Float, nullable | موقع الخدمة |
| `address` | String(255), nullable | العنوان النصي |
| `assigned_technician_id` | Integer FK -> technicians.id, nullable | الفني المسند |
| `technician_report` | Text, nullable | تقرير الفني عند الإكمال |
| `customer_rating` | Float, nullable | تقييم العميل لهذا الطلب |
| `created_at` | DateTime, server default now | وقت الإنشاء |

### `request_services`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف السجل |
| `request_id` | Integer FK -> requests.id | الطلب |
| `service_id` | Integer FK -> services.id | الخدمة المرتبطة |
| `service_type_name` | String(100), nullable | اسم/نوع الخدمة نصياً |
### `reviews`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف المراجعة |
| `technician_id` | Integer FK -> technicians.id | الفني |
| `request_id` | Integer FK -> requests.id | الطلب |
| `accepted` | Boolean, default false | حالة قبول من جدول legacy |
| `confirmed` | Boolean, default false | حالة تأكيد من جدول legacy |
| `status` | String(30), nullable | حالة legacy من منظور الفني |

### `ratings`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف التقييم |
| `customer_id` | Integer FK -> customers.id | العميل المقيم |
| `technician_id` | Integer FK -> technicians.id | الفني المقيم |
| `score` | Float | قيمة التقييم |
| `comment` | Text, nullable | تعليق اختياري |
| `created_at` | DateTime, server default now | وقت التقييم |

### `otp_verifications`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف OTP |
| `phone` | String(20), indexed | رقم الهاتف |
| `code` | String(6) | رمز OTP |
| `user_type` | String(10) | `customer` أو `technician` |
| `expires_at` | DateTime | وقت انتهاء الرمز |
| `created_at` | DateTime, server default now | وقت إنشاء الرمز |

### `notifications`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف الإشعار |
| `user_id` | Integer | معرف المستخدم (بدون FK لأن المستخدم قد يكون عميل أو فني) |
| `user_type` | String(20) | `customer` أو `technician` |
| `title` | String(255) | عنوان الإشعار |
| `body` | Text | نص الإشعار |
| `type` | String(50) | نوع الإشعار |
| `is_read` | Boolean default false | حالة القراءة |
| `created_at` | DateTime, server default now | وقت الإنشاء |

### `request_assignments`
| العمود | النوع | الغرض |
|---|---|---|
| `id` | Integer PK | معرف عملية الإسناد |
| `request_id` | Integer FK -> requests.id | الطلب |
| `technician_id` | Integer FK -> technicians.id | الفني المرشح/المسند |
| `assigned_at` | DateTime, server default now | وقت الإسناد |
| `status` | String(20), default `pending` | حالة الإسناد (`pending/accepted/rejected/timeout`) |
| `timeout_at` | DateTime, nullable | وقت انتهاء مهلة الرد |

### English
All database tables above are taken directly from SQLAlchemy models under `app/models`. They include customer/technician core data, request lifecycle data, OTP records, ratings, notifications, and request assignment timeout tracking.

---

## 5. API Endpoints
### العربية
**Base URL:** غالباً `http://localhost:8000`

#### System
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `GET /` | No | None | `{ "message": str, "docs": "/docs" }` | يعرض رسالة ترحيب وروابط التوثيق |
| `GET /api/health` | No | None | `{ "status": "ok" }` | فحص صحة الخدمة |

#### Auth (`/api/auth`)
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `POST /api/auth/send-otp` | No | Body: `{ phone, user_type }` | `{ "message": ... }` | يولد OTP ويحفظه ويرسله SMS |
| `POST /api/auth/verify-otp` | No | Body: `{ phone, code, user_type }` | Either `{ verified:true, registered:false, phone }` or token payload | يتحقق من OTP ويُرجع توكن إذا المستخدم مسجل |
| `POST /api/auth/register/customer` | No | Body: `{ name, phone, password }` | `{ access_token, token_type, user_id, user_type }` | تسجيل عميل جديد |
| `POST /api/auth/register/technician` | No | Body: `{ name, phone, password, service_ids[] }` | `{ access_token, token_type, user_id, user_type }` | تسجيل فني وربط خدماته |
| `POST /api/auth/login` | No | Body: `{ phone, password, user_type }` | `{ access_token, token_type, user_id, user_type }` | تسجيل دخول وتوليد JWT |
| `POST /api/auth/reset-password` | No | Body: `{ phone, code, new_password, user_type? }` | `{ "message": ... }` | إعادة تعيين كلمة المرور بعد OTP |
| `POST /api/auth/change-password` | Bearer (`customer`/`technician`) | Body: `{ current_password, new_password }` | `{ "message": ... }` | تغيير كلمة المرور أثناء تسجيل الدخول |
| `POST /api/auth/update-fcm-token` | Bearer (`customer`/`technician`) | Body: `{ fcm_token }` | `{ "success": true }` | تحديث FCM token للمستخدم الحالي |

#### Services (`/api/services`)
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `GET /api/services/` | No | None | `[{ id, name }]` | إرجاع قائمة الخدمات |

#### Technicians (`/api/technicians`)
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `GET /api/technicians/nearby` | No | Query: `service_id`, `customer_lat`, `customer_lng`, `limit<=50` | `[{ id, name, phone, status, availability_status, lat, lng, avg_rating, distance_km }]` | يجلب فنيين حسب الخدمة، ثم يرتبهم حسب التقييم والمسافة |

#### Requests (`/api/requests`)
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `GET /api/requests/` | Bearer (`customer` or `technician`) | None | `RequestResponse[]` | يعرض طلبات المستخدم الحالي (عميل: طلباته / فني: المسند له) |
| `POST /api/requests/` | Bearer (`customer`) | Body: `{ note?, image_url?, service_ids[], service_type_names?, lat?, lng?, address? }` | `RequestResponse` | ينشئ طلب، ثم يحاول إسناد أفضل فني ويبدأ timeout |
| `POST /api/requests/{request_id}/accept` | Bearer (`technician`) | Path: `request_id` | `RequestResponse` | قبول الطلب وتحديث حالة الإسناد وتحديث معدل القبول وإشعار العميل |
| `POST /api/requests/{request_id}/complete` | Bearer (`technician`) | Path + Body: `{ report }` | `RequestResponse` | إكمال الطلب، تحديث معدل الإكمال، وإشعار العميل |
| `POST /api/requests/{request_id}/rate` | Bearer (`customer`) | Path + Body: `{ rating }` | `RequestResponse` | تقييم الطلب/الفني، تحديث متوسط تقييم الفني، وإشعار الفني |

`RequestResponse` shape:
```json
{
  "id": 1,
  "customer_id": 1,
  "note": "...",
  "image_url": "...",
  "status": "pending|assigned|accepted|completed|cancelled",
  "created_at": "datetime",
  "service_ids": [1],
  "service_type_names": ["..."],
  "lat": 0,
  "lng": 0,
  "address": "...",
  "assigned_technician_id": 2,
  "assigned_technician_name": "...",
  "assigned_technician_rating": 4.5,
  "technician_report": "...",
  "customer_rating": 5
}
```

#### Notifications (`/api/notifications`)
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `GET /api/notifications/?unread_only=0|1` | Bearer | Query: `unread_only` optional | `{ "results": [{ id, title, body, type, is_read, created_at }] }` | جلب الإشعارات الحالية للمستخدم |
| `POST /api/notifications/{notification_id}/read` | Bearer | Path: `notification_id` | `{ "success": true }` | تعليم إشعار محدد كمقروء |
| `POST /api/notifications/read-all` | Bearer | None | `{ "success": true, "updated": <int> }` | تعليم كل إشعارات المستخدم كمقروءة |
| `DELETE /api/notifications/{notification_id}` | Bearer | Path: `notification_id` | `{ "success": true }` | حذف إشعار محدد |

#### Technician Profile (`/api/technician/profile`)
| Method + Path | Auth | Input | Response | What it does |
|---|---|---|---|---|
| `GET /api/technician/profile/status` | Bearer (`technician`) | None | `{ "status": "..." }` | جلب حالة حساب الفني |
| `POST /api/technician/profile/documents` | Bearer (`technician`) | Multipart files: `profile_photo`, `id_card_photo` | `{ "success": true, "status": "pending_approval" }` | رفع مستندات الفني وتحويل حالته لمراجعة |
| `PUT /api/technician/profile/status` | Bearer (`admin`) | Body: `{ technician_id, status }` | `{ "success": true }` | تغيير حالة الفني (قبول/رفض/مراجعة) مع إشعار |

### English
All endpoints above are documented directly from `main.py` router registration and the router files in `app/api/*`.

---

## 6. Business Logic
### العربية
### 6.1 منطق إسناد الفني (Scoring Formula)
في `app/services/assignment_service.py` يتم اختيار الفني الأفضل عبر:
1. فلترة الفنيين حسب:
- نفس `service_id`.
- `technician.status` ضمن (`approved` أو `available`).
- `availability_status` ضمن (`available` أو `NULL`).
- استبعاد أي فني موجود في `excluded_ids`.
2. حساب النقاط لكل فني:

```text
distance_score = (1 / (distance_km + 0.1)) * 0.4   # إذا كانت الإحداثيات متوفرة
rating_score   = ((avg_rating or 0) / 5) * 0.4
accept_score   = (acceptance_rate or 0) * 0.1
complete_score = (completion_rate or 0) * 0.1

total_score = distance_score + rating_score + accept_score + complete_score
```
- إذا لا توجد إحداثيات عميل/فني: `distance_score = 0`.
- يتم اختيار أعلى `total_score`.

### 6.2 مهلة 5 دقائق (Timeout)
عند إنشاء إسناد جديد:
- يتم ضبط `timeout_at = now + 5 minutes`.
- يتم جدولة مهمة background (`check_assignment_timeout`) بعد 300 ثانية.
- إذا ظل `RequestAssignment.status = pending` بعد 5 دقائق:
  - يتحول إلى `timeout`.
  - يعاد حساب `acceptance_rate` للفني.
  - يتم محاولة إسناد فني آخر لنفس الطلب مع استبعاد الفنيين الذين تم تجربتهم سابقاً.
  - إذا وجد فني جديد: يتم إنشاء Assignment جديد + إعادة الجدولة + إشعار الفني الجديد.
  - إذا لم يوجد: يتحول الطلب إلى `cancelled` + إشعار العميل بعدم توفر فنيين.

### 6.3 OTP
- `send-otp`:
  - يولد رمز 6 أرقام.
  - يحذف أي OTP سابق لنفس `phone + user_type`.
  - يحفظ OTP بصلاحية 5 دقائق.
  - يرسله عبر SMS provider (أو يطبع في وضع dev إذا لم يضبط SMS API).
- `verify-otp`:
  - يتحقق من الهاتف + الرمز + النوع + عدم انتهاء الصلاحية.
  - عند النجاح: يحذف OTP مباشرة (one-time use).
  - إذا كان المستخدم مسجلاً: يرجع JWT.

### 6.4 FCM Notifications
- عند تحميل `firebase_service.py`:
  - يحاول `firebase_admin.initialize_app()` باستخدام `FIREBASE_CREDENTIALS_PATH`.
- `notify_user(...)`:
  - يبحث عن `fcm_token` حسب نوع المستخدم.
  - إذا token موجود: يرسل push عبر FCM.
  - دائماً يحفظ سجل في جدول `notifications`.
- يتم استخدام `notify_user` في:
  - إنشاء طلب (إشعار فني جديد).
  - قبول الطلب (إشعار العميل).
  - إكمال الطلب (إشعار العميل).
  - التقييم (إشعار الفني).
  - قبول/رفض حساب الفني من admin.
  - حالة عدم توفر فنيين بعد timeout.

### English
### 6.1 Technician assignment
The assignment engine filters eligible technicians then computes a weighted score:
- Distance: `40%`
- Average rating: `40%`
- Acceptance rate: `10%`
- Completion rate: `10%`

The technician with the highest total score is selected.

### 6.2 5-minute timeout flow
Each pending assignment is checked after 300 seconds. If still pending, it becomes `timeout`, technician metrics are updated, and the system attempts re-assignment to the next best technician. If no candidate is found, the request is marked `cancelled` and the customer is notified.

### 6.3 OTP flow
OTP codes are generated per `(phone, user_type)`, expire in 5 minutes, and are consumed (deleted) upon successful verification.

### 6.4 FCM flow
The app initializes Firebase Admin from service account credentials, sends push notifications when possible, and always stores a notification record in DB.

---

## 7. Setup & Installation
### العربية
### من الصفر (Step-by-step)
1. **Clone المشروع**
```bash
git clone <repo-url>
cd fi_khedmtak_backend
```

2. **إنشاء وتفعيل البيئة الافتراضية**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

3. **تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

4. **إعداد ملف `.env`**
```bash
# انسخ القالب
cp .env.example .env
# أو على ويندوز:
copy .env.example .env
```
ثم عدّل القيم المطلوبة (خصوصاً قاعدة البيانات وJWT).

5. **إعداد Firebase credentials**
- ضع ملف Service Account JSON باسم `firebase_credentials.json` في جذر المشروع.
- أو غيّر المسار عبر `FIREBASE_CREDENTIALS_PATH` في `.env`.

6. **تشغيل الـ migrations/إنشاء الجداول**
```bash
python init_db.py
python create_tables.py
python migrate_requests_v2.py
python migrate_v3.py
```

7. **Seed البيانات الأساسية**
```bash
python seed_services.py
```

8. **تشغيل الخادم**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
ثم افتح:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### English
### From zero (Step-by-step)
1. Clone repository.
2. Create and activate virtual environment.
3. Install dependencies from `requirements.txt`.
4. Create `.env` from `.env.example` and set values.
5. Add Firebase service account JSON.
6. Run DB initialization + migrations.
7. Seed default services.
8. Run Uvicorn and open `/docs`.

---

## 9. Environment Variables
### العربية
| المتغير | مطلوب؟ | مثال آمن | الوصف |
|---|---|---|---|
| `DATABASE_URL` | نعم | `mysql+pymysql://<user>:<password>@localhost:3306/fi_khedmtak` | رابط الاتصال بقاعدة البيانات |
| `SECRET_KEY` | نعم | `change-this-in-production` | مفتاح توقيع JWT |
| `ALGORITHM` | اختياري | `HS256` | خوارزمية JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | اختياري | `10080` | مدة صلاحية التوكن بالدقائق |
| `SMS_API_URL` | اختياري | `https://sms-provider.example/send` | Endpoint مزود SMS |
| `SMS_API_KEY` | اختياري | `your-sms-api-key` | مفتاح مزود SMS |
| `FIREBASE_CREDENTIALS_PATH` | اختياري (لكن مطلوب لتفعيل FCM فعلياً) | `firebase_credentials.json` | مسار ملف Firebase Service Account |

> ملاحظة: ملف `.env` الحالي في المشروع لا يحتوي `FIREBASE_CREDENTIALS_PATH`، لكن `config.py` يدعم قيمة افتراضية `firebase_credentials.json`.

### English
| Variable | Required? | Safe Example | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Yes | `mysql+pymysql://<user>:<password>@localhost:3306/fi_khedmtak` | Database connection string |
| `SECRET_KEY` | Yes | `change-this-in-production` | JWT signing key |
| `ALGORITHM` | Optional | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `10080` | JWT expiration in minutes |
| `SMS_API_URL` | Optional | `https://sms-provider.example/send` | SMS provider endpoint |
| `SMS_API_KEY` | Optional | `your-sms-api-key` | SMS provider API key |
| `FIREBASE_CREDENTIALS_PATH` | Optional (required for real FCM push) | `firebase_credentials.json` | Firebase service account file path |

---

## 10. Notification Types
### العربية
| النوع | أين يُستخدم | متى يُطلق | المستلم |
|---|---|---|---|
| `new_request` | `requests.create` + `assignment_service` | عند إسناد طلب جديد لفني | فني |
| `request_accepted` | `requests.accept` | عند قبول الفني للطلب | عميل |
| `request_completed` | `requests.complete` | عند إكمال الطلب | عميل |
| `request_rated` | `requests.rate` | عند تقييم العميل للفني | فني |
| `account_approved` | `technician_profile.update_status` | عند قبول حساب الفني | فني |
| `account_rejected` | `technician_profile.update_status` | عند رفض حساب الفني | فني |
| `no_technicians` | `assignment_service.check_assignment_timeout` | بعد انتهاء المحاولات وعدم وجود فني متاح | عميل |
| `admin_broadcast` | معرف في نموذج `Notification` فقط | غير مستخدم حالياً في الكود | غير مطبق |

### English
| Type | Trigger Location | When It Triggers | Receiver |
|---|---|---|---|
| `new_request` | request creation / reassignment | New request assigned to a technician | Technician |
| `request_accepted` | request accept endpoint | Technician accepts request | Customer |
| `request_completed` | request complete endpoint | Technician marks request completed | Customer |
| `request_rated` | request rate endpoint | Customer submits rating | Technician |
| `account_approved` | technician status update endpoint | Admin approves technician account | Technician |
| `account_rejected` | technician status update endpoint | Admin rejects technician account | Technician |
| `no_technicians` | timeout assignment engine | No technician available after retries | Customer |
| `admin_broadcast` | model enum-like comment only | Defined but not emitted in current code | Not implemented |

---

## 11. Request Status Flow
### العربية
### حالات جدول `requests`
- `pending`: عند إنشاء الطلب بدون إسناد فوري.
- `assigned`: عند إنشاء Assignment لفني.
- `accepted`: عند قبول الفني الطلب.
- `completed`: عند إنهاء الفني الطلب وإرسال التقرير.
- `cancelled`: إذا انتهت كل محاولات الإسناد بدون فني.

### مخطط تدفق مبسط
```text
create request
   -> pending (if no technician)
   -> assigned (if technician found)
assigned
   -> accepted (technician accepts)
   -> cancelled (after timeout retries exhausted)
accepted
   -> completed (technician completes)
completed
   -> rate endpoint adds rating (status stays completed)
```

### حالات جدول `request_assignments`
- `pending`: الفني لم يرد بعد.
- `accepted`: الفني قبل الطلب.
- `rejected`: قيمة معرفة بالنموذج (حالياً لا يوجد endpoint يضبطها).
- `timeout`: انتهت مهلة 5 دقائق بدون قبول.

### English
### `requests` statuses
- `pending` -> request created but not assigned.
- `assigned` -> assignment record created for technician.
- `accepted` -> technician accepted.
- `completed` -> technician completed with report.
- `cancelled` -> no technician available after timeout retries.

### `request_assignments` statuses
- `pending`, `accepted`, `rejected` (defined, not currently set by endpoint), `timeout`.

---

## 12. Known Limitations
### العربية
- لا يوجد **Admin panel** فعلي حتى الآن.
- لا يوجد نموذج أو endpoints كاملة لإدارة مستخدم admin (يوجد فقط تحقق `current_user["type"] == "admin"` في endpoint واحد).
- لا يوجد **Live tracking** لموقع الفني/الطلب.
- لا يوجد **Chat** بين العميل والفني.
- لا توجد اختبارات تلقائية (unit/integration tests) ضمن المشروع الحالي.
- لا يوجد Alembic؛ الـ migrations الحالية سكربتات يدوية (`migrate_*.py`).
- حقل `technician.status` يستخدم بشكل legacy ومتداخل مع مفهوم حالة الحساب، بينما `availability_status` للحالة التشغيلية.
- بعض المدخلات تستخدم `dict` مباشرة بدل Schemas (مثال: `complete/rate/update status`) مما يقلل صرامة التحقق.

### English
- No full admin panel exists yet.
- Admin user model/auth flow is not fully implemented (only an admin-type check in one endpoint).
- No live tracking.
- No real-time chat.
- No automated tests included.
- No Alembic migrations; migration scripts are manual.
- `technician.status` is legacy/overloaded; `availability_status` carries operational availability.
- Some endpoints still accept raw `dict` bodies instead of strict Pydantic schemas.
