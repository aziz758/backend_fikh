# Fi Khedmtak Backend API

## 1. Project Overview
Fi Khedmtak is a FastAPI backend for an on-demand field service platform that connects customers with technicians.

### Current capabilities
- OTP-based authentication and account access.
- Customer and technician registration and login.
- Service request creation with automatic technician assignment.
- Request lifecycle: assign, accept, complete, and rate.
- In-app notifications plus Firebase FCM push notifications.
- Technician document upload and account status review.
- Admin endpoints for statistics, users, requests, ratings, and broadcast notifications.

### User types
- `customer`: creates requests, tracks progress, rates technicians.
- `technician`: receives requests, accepts/completes requests, uploads documents.
- `admin`: reviews technicians, monitors platform data, manages users.

---

## 2. Tech Stack
- `fastapi`: REST API framework.
- `uvicorn[standard]`: ASGI server for development/runtime.
- `sqlalchemy`: ORM and data access layer.
- `pymysql`: MySQL driver.
- `python-jose[cryptography]`: JWT creation/validation.
- `passlib[bcrypt]` + `bcrypt`: password hashing.
- `python-multipart`: file upload support.
- `httpx`: async HTTP client for SMS OTP providers.
- `python-dotenv`: loading environment variables.
- `firebase-admin`: FCM push notifications.

---

## 3. Project Structure

```text
app/
  api/
    admin.py
    auth.py
    dependencies.py
    notifications.py
    requests.py
    services.py
    technician_profile.py
    technicians.py
  models/
    customer.py
    notification.py
    otp.py
    rating.py
    request.py
    request_assignment.py
    review.py
    service.py
    technician.py
  schemas/
    auth.py
    customer.py
    request_schema.py
    service.py
    technician.py
  services/
    assignment_service.py
    auth_service.py
    firebase_service.py
    sms_service.py
  config.py
  database.py
main.py
init_db.py
create_tables.py
migrate_requests_v2.py
migrate_v3.py
seed_services.py
admin_seed.py
```

---

## 4. Database Tables
Main tables defined by SQLAlchemy models:
- `customers`
- `technicians`
- `technician_services`
- `services`
- `requests`
- `request_services`
- `request_assignments`
- `ratings`
- `reviews`
- `otp_verifications`
- `notifications`

---

## 5. API Endpoints

### System
- `GET /` - API root message.
- `GET /api/health` - health check.

### Auth (`/api/auth`)
- `POST /send-otp`
- `POST /verify-otp`
- `POST /register/customer`
- `POST /register/technician`
- `POST /login`
- `POST /reset-password`
- `POST /change-password`
- `POST /update-fcm-token`

### Services (`/api/services`)
- `GET /`

### Technicians (`/api/technicians`)
- `GET /nearby`

### Requests (`/api/requests`)
- `GET /`
- `POST /`
- `POST /{request_id}/accept`
- `POST /{request_id}/complete`
- `POST /{request_id}/rate`

### Notifications (`/api/notifications`)
- `GET /`
- `POST /{notification_id}/read`
- `POST /read-all`
- `DELETE /{notification_id}`

### Technician Profile (`/api/technician/profile`)
- `GET /status`
- `POST /documents`
- `PUT /status`

### Admin (`/api/admin`)
- `GET /statistics`
- `GET /technicians`
- `PUT /technicians/{technician_id}/status`
- `GET /requests`
- `GET /ratings`
- `POST /notifications/broadcast`
- `GET /users`
- `DELETE /users/{user_id}`
- `GET /dashboard`

---

## 6. Request Assignment Logic
Technician scoring combines:
- distance (when coordinates are available),
- technician average rating,
- acceptance rate,
- completion rate.

When a request is assigned:
- a 5-minute timeout is started,
- if pending after timeout, assignment is marked `timeout`,
- system tries another technician,
- if no technician is available, request becomes `cancelled` and customer is notified.

---

## 7. Setup and Installation

### 1) Create virtual environment
Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:
```bash
python -m venv venv
source venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment
```bash
copy .env.example .env
```
Update `.env` values for your database, JWT key, and integrations.

### 4) Initialize database and schema
```bash
python init_db.py
python create_tables.py
python migrate_requests_v2.py
python migrate_v3.py
python seed_services.py
```

### 5) Run server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 8. Environment Variables
Required:
- `DATABASE_URL`
- `SECRET_KEY`

Optional:
- `ALGORITHM` (default `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default `10080`)
- `SMS_API_URL`
- `SMS_API_KEY`
- `FIREBASE_CREDENTIALS_PATH` (default `firebase_credentials.json`)

---

## 9. Notification Types
- `new_request`
- `request_accepted`
- `request_completed`
- `request_rated`
- `account_approved`
- `account_rejected`
- `no_technicians`
- `admin_broadcast`

---

## 10. Request Status Flow
### `requests`
- `pending`
- `assigned`
- `accepted`
- `completed`
- `cancelled`

### `request_assignments`
- `pending`
- `accepted`
- `rejected`
- `timeout`

---

## 11. Known Limitations
- Manual migration scripts are used (no Alembic workflow yet).
- Limited automated test coverage in current codebase.
- Some endpoints still accept raw `dict` payloads instead of strict schemas.
- No live tracking/chat features yet.
