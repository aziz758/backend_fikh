# Fi Khedmtak Backend API

## 1. Project Overview
Fi Khedmtak is a FastAPI backend for an on-demand field service platform that connects customers with technicians.

### Current capabilities
- OTP-based authentication and account access.
- Customer and technician registration and login.
- Service request creation with automatic technician assignment.
- Request lifecycle: assign, accept, complete, and rate.
- In-app notifications plus Firebase FCM push notifications.
- Optional Firebase Realtime sync for request state and technician live location.
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
migrate_v4.py
migrate_v5.py
migrate_v6.py
migrate_v7.py
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
  - query: `service_id`, `customer_lat`, `customer_lng`, optional `max_distance_km`

### Requests (`/api/requests`)
- `GET /`
  - query: `status` (optional), `page` (default `1`), `limit` (default `20`, max `100`)
  - response: paginated object `{ results, total, page, limit }`
- `GET /{request_id}`
- `POST /`
- `POST /{request_id}/accept`
- `POST /{request_id}/reject` (requires rejection reason)
- `POST /{request_id}/complete`
- `POST /{request_id}/rate`
  - request responses include direct navigation links when `lat/lng` are available:
    `google_maps_directions_url`, `apple_maps_directions_url`, `google_navigation_uri`, `geo_navigation_uri`
  - canonical contract only (legacy `wrapped` query/body is removed)

### Notifications (`/api/notifications`)
- `GET /`
  - query: `unread_only` (optional), `page` (default `1`), `limit` (default `20`, max `100`)
  - response: paginated object `{ results, total, page, limit }`
- `GET /unread-count`
- `POST /{notification_id}/read`
- `POST /read-all`
- `DELETE /{notification_id}`

### Customer Profile (`/api/customer/profile`)
- `GET /me`
- `PUT /me`

### Technician Profile (`/api/technician/profile`)
- `GET /me`
- `GET /status`
- `POST /documents`
- `PUT /location`
- `PUT /availability`
- `PUT /work-settings`

Profile API note:
- canonical profile routes are `/me` under each profile prefix.
- legacy aliases remain callable for backward compatibility but are hidden from docs.
- technician account status updates are admin-only via:
  `PUT /api/admin/technicians/{technician_id}/status`

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
- when technician rejects, the rejection reason is stored and exposed in request logs.

Eligibility note:
- technicians must have a saved and fresh location (`lat` + `lng`) to receive new assignments.
- if location expires (based on `TECHNICIAN_LOCATION_TTL_MINUTES`), technician is moved to `offline` automatically.
- assignment/nearby matching respects `TECHNICIAN_MAX_SERVICE_DISTANCE_KM` when customer location is available.
- technicians in `on_break` are excluded from receiving new assignments.
- technician-specific `service_radius_km` and working hours (`work_start_time`, `work_end_time`, `work_days`) are enforced for matching.

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
python migrate_v4.py
python migrate_v5.py
python migrate_v6.py
python migrate_v7.py
python migrate_v8_otp_hash.py
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
- `FIREBASE_DATABASE_URL` (required only for Realtime Database sync)
- `TECHNICIAN_WORKING_HOURS_TIMEZONE` (default `Asia/Riyadh`)
- `TECHNICIAN_LOCATION_TTL_MINUTES` (default `5`)
- `TECHNICIAN_MAX_SERVICE_DISTANCE_KM` (default `20`)
- `TECHNICIAN_PRIORITY_DISTANCE_WEIGHT` (default `0.5`)
- `TECHNICIAN_PRIORITY_RATING_WEIGHT` (default `0.25`)
- `TECHNICIAN_PRIORITY_ACCEPTANCE_WEIGHT` (default `0.15`)
- `TECHNICIAN_PRIORITY_COMPLETION_WEIGHT` (default `0.1`)

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
- Realtime Database rules and App Check hardening are not configured yet.

---

## 12. Security Hardening Plan
This plan intentionally splits the security work into small, reviewable tasks so the project workflow stays stable.

### Task 0 - Document the implementation plan
Status: Done.

Completed:
- Added this section to track the security hardening work.
- No application code was changed in this task.

Remaining:
- Continue implementing the remaining tasks one at a time.

### Task 1 - Block inactive accounts
Status: Done.

Goal:
- Prevent users with `status = inactive` from logging in or using protected endpoints.

Completed:
- Update login checks for customers and technicians.
- Update authentication dependencies so existing tokens for inactive users are rejected.
- Update OTP verification login so registered inactive accounts cannot receive a new access token.
- Inactive accounts now receive `403 Account is inactive`.

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Manually verify inactive customers and technicians receive an authentication or authorization error when test data is available.
- Verified with:
  - `venv\Scripts\python.exe -B -c "from main import app; print(app.title, app.version)"`
  - Python AST parse for all project `.py` files.
  - Direct dependency check confirming an inactive token returns `403 Account is inactive`.

Remaining:
- Add automated tests for inactive customer and technician login/token behavior.

### Task 2 - Require OTP verification before registration
Status: Done.

Goal:
- Ensure customer and technician registration only happens after a successful OTP verification.

Completed:
- Return a short-lived `registration_token` from `POST /api/auth/verify-otp` when the phone is verified but not registered.
- Require that token in `POST /api/auth/register/customer` and `POST /api/auth/register/technician`.
- Registration tokens are scoped to the verified phone number and user type.

Validation:
- Registration without a valid registration token fails.
- Registration after OTP verification succeeds.
- Existing login flow remains unchanged.
- Verified with:
  - FastAPI app import.
  - Python AST parse for all project `.py` files.
  - Direct registration-token check confirming valid, wrong-phone, and wrong-user-type behavior.

Remaining:
- Add API-level automated tests for the full `send-otp` -> `verify-otp` -> `register` flow.
- Consider adding a one-time-use server-side registration session if token reuse becomes a concern.

### Task 3 - Harden OTP generation and storage
Status: Done.

Goal:
- Make OTP generation and storage safer while keeping the current UX.

Completed:
- Use a cryptographically safer OTP generator.
- Store a hash of the OTP instead of the plain code.
- Keep temporary compatibility with existing unexpired OTP records if needed during rollout.
- Add `migrate_v8_otp_hash.py` to expand `otp_verifications.code` for hashed OTP values.
- Update the database setup steps to include `migrate_v8_otp_hash.py`.

Validation:
- OTP verification succeeds for valid codes.
- OTP verification fails for expired, reused, or invalid codes.
- Verified with:
  - FastAPI app import.
  - Python AST parse for all project `.py` files.
  - Direct OTP helper checks for generated format, hashed-code match, wrong-code rejection, and legacy plain-code compatibility.

Remaining:
- Run `python migrate_v8_otp_hash.py` against each existing environment before deploying hashed OTP storage.
- Add API-level automated tests for OTP verification success, invalid code, expiration, and reuse.

### Task 4 - Validate image uploads
Status: Done.

Goal:
- Reject unsafe or unexpectedly large uploads before saving files.

Completed:
- Allow only approved image content types and extensions, such as JPEG, PNG, and WebP.
- Add a maximum upload size of 5 MB.
- Normalize generated filenames and saved paths.
- Apply the shared validation helper to request images, profile images, and technician document images.
- Preserve the existing response shape for request/profile image upload endpoints.

Validation:
- Valid images upload successfully.
- Unsupported file types and oversized files are rejected.
- Existing request/profile image responses keep the same response shape.
- Verified with:
  - FastAPI app import.
  - Python AST parse for all project `.py` files.
  - Direct upload helper checks for valid JPEG, unsupported content type, mismatched extension/content type, and oversized image rejection.

Remaining:
- Add API-level automated tests for upload endpoints.
- Task 5 still needs to make technician identity documents private/protected instead of public static files.

### Task 5 - Protect technician identity documents
Status: Done.

Goal:
- Avoid exposing sensitive technician documents as normal public static files.

Completed:
- Move identity document storage behind a private path or a protected download endpoint.
- Keep public profile images separate from private ID card documents.
- Restrict document access to the owning technician and admins.
- New ID card uploads are saved under `private_uploads/technician_documents`.
- New technician profile images are saved under public `/uploads/technician_profiles`.
- Direct public access to legacy `/uploads/documents/*` paths is blocked.
- Existing legacy ID document paths can still be served through protected endpoints:
  - technician self access: `GET /api/technician/profile/documents/id-card`
  - admin access: `GET /api/admin/technicians/{technician_id}/documents/id-card`

Validation:
- Admins can review documents.
- Technicians can access their own submitted documents.
- Public users cannot fetch ID card documents directly.
- Verified with:
  - FastAPI app import.
  - Python AST parse for all project `.py` files.
  - Route inventory check confirming the protected technician/admin document endpoints exist.
  - TestClient check confirming `/uploads/documents/example.jpg` returns `404`.

Remaining:
- Add API-level automated tests for document access permissions.
- Consider migrating old files out of `uploads/documents` into `private_uploads/technician_documents`.
- Consider adding signed short-lived download URLs if external storage is introduced later.

### Task 6 - Update this plan after each task
Goal:
- Keep the README as the source of truth for what was completed and what remains.

Expected changes:
- Mark each completed task as done.
- Add a short note describing what changed.
- Add the verification command or manual check used.

Validation:
- README reflects the current implementation state after every task.

---

## 13. Frontend Integration Notes
These notes summarize the backend changes that require frontend updates.

### Auth and registration
`POST /api/auth/send-otp`:
- No frontend request change.
- Keep sending:
```json
{
  "phone": "0501234567",
  "user_type": "customer"
}
```

`POST /api/auth/verify-otp`:
- If the phone is already registered, the response still returns an access token.
- If the phone is not registered, the response now includes `registration_token`.

Unregistered phone response:
```json
{
  "verified": true,
  "registered": false,
  "phone": "0501234567",
  "registration_token": "..."
}
```

Registered phone response:
```json
{
  "verified": true,
  "registered": true,
  "access_token": "...",
  "token_type": "bearer",
  "user_id": 1,
  "user_type": "customer"
}
```

Frontend action:
- Store `registration_token` temporarily after OTP verification.
- Send it in the next registration request.
- Do not persist it like a login token.

`POST /api/auth/register/customer` now requires:
```json
{
  "name": "Customer Name",
  "phone": "0501234567",
  "password": "secret123",
  "registration_token": "..."
}
```

`POST /api/auth/register/technician` now requires:
```json
{
  "name": "Technician Name",
  "phone": "0501234567",
  "password": "secret123",
  "registration_token": "...",
  "service_ids": [1, 2]
}
```

Error handling:
- Invalid or expired registration token returns `400`.
- Inactive accounts now return `403 Account is inactive` from login, OTP-login, or protected endpoints.

### Image uploads
The upload response shape is unchanged for request/profile images.

Allowed image types:
- JPEG: `.jpg`, `.jpeg`
- PNG: `.png`
- WebP: `.webp`

Maximum size:
- `5 MB`

Rejected uploads:
- Unsupported type: `400`
- Extension/content-type mismatch: `400`
- Oversized image: `413`

Request image upload:
- `POST /api/uploads/request-image/`
- Form field can still be `file` or `image`.
- Response stays:
```json
{
  "image_url": "/uploads/...",
  "url": "/uploads/..."
}
```

Profile image upload:
- `POST /api/uploads/profile-image/`
- Form field: `file`
- Response stays:
```json
{
  "image_url": "/uploads/..."
}
```

### Technician documents
`POST /api/technician/profile/documents`:
- Still accepts multipart fields:
  - `profile_photo`
  - `id_card_photo`
- Both files must pass the new image validation rules.
- The response shape is unchanged:
```json
{
  "success": true,
  "status": "pending_approval"
}
```

Important frontend behavior change:
- Do not open `id_card_photo_url` as a public `/uploads/...` file anymore.
- The ID card document is now protected.
- For the technician's own profile, `id_card_photo_url` is returned as:
  - `/api/technician/profile/documents/id-card`
- For admin technician lists, `id_card_photo_url` is returned as:
  - `/api/admin/technicians/{technician_id}/documents/id-card`

How to display protected ID card images:
- Fetch the protected URL with the bearer token.
- Convert the response blob to an object URL before rendering in an `<img>`.
- Handle `404` as "document missing or not accessible".

Public access blocked:
- `/uploads/documents/*` now returns `404`.
- New ID cards are stored privately under `private_uploads/technician_documents`.
- New technician profile photos remain public under `/uploads/technician_profiles`.

### Backend deployment note for frontend testing
Before testing OTP registration on an existing database, run:
```bash
python migrate_v8_otp_hash.py
```

Without this migration, hashed OTP values may not fit in the old `otp_verifications.code` column.

---

## 14. Top Technicians by Area Plan
This plan tracks the new customer-facing directory screen where customers can browse multiple highly rated technicians by service and area.

### Product behavior
- When a customer selects a service, such as `كهربائي`, the frontend should show multiple approved technicians, not only one technician.
- This browsing screen must prioritize ratings, rating count, and positive comments.
- Technicians do not need to be currently `available`.
- Technicians do not need to have a fresh live location for this screen.
- Live location and availability checks remain important only for immediate request assignment flows.

### Location model recommendation
Use administrative areas for browsing and ranking:
- `governorates`
- `districts`

Keep live coordinates separate:
- `lat`
- `lng`
- `location_updated_at`

Reason:
- governorate/district is stable and useful for search, filtering, and reports.
- `lat/lng` is dynamic and useful for distance, maps, and real-time assignment.

### Planned API behavior
Add a new endpoint for browsing top technicians:

```http
GET /api/technicians/top
```

Expected query parameters:
- `service_id`
- `governorate_id`
- `district_id` optional
- `limit` optional

Expected response data per technician:
- `id`
- `name`
- `profile_photo_url`
- `services`
- `governorate`
- `district`
- `avg_rating`
- `total_ratings`
- `positive_comments`
- `availability_status`
- `acceptance_rate`
- `completion_rate`

This endpoint should not use these filters:
- `availability_status == available`
- fresh `location_updated_at`
- required `lat/lng`
- distance from customer

It should use these filters:
- technician is `approved`
- technician provides the selected service
- technician matches the requested governorate/district or serves that area

### Ranking recommendation
Sort technicians using a weighted ranking, not only raw average rating.

Recommended priority:
- exact district match
- governorate match
- average rating
- total rating count
- positive comment count
- completion rate
- acceptance rate

Reason:
- A technician with one `5.0` rating should not always outrank a technician with many strong ratings.

### Task 0 - Document the plan
Status: Done.

Completed:
- Added this plan to define the feature scope before changing code.
- Clarified that top-technician browsing is separate from live nearby matching.
- Clarified that this screen can show offline technicians and technicians without fresh location.
- Documented the proposed endpoint contract for frontend planning.

Remaining:
- Continue with Task 1.

### Task 1 - Add governorates and districts
Status: Pending.

Goal:
- Add stable administrative location tables for customers, technicians, and requests.

Expected changes:
- Add `Governorate` model.
- Add `District` model.
- Add migration script.
- Add seed script for initial governorates and districts.
- Add location list endpoints:
  - `GET /api/locations/governorates`
  - `GET /api/locations/districts?governorate_id=...`

### Task 2 - Add area fields to customers and technicians
Status: Pending.

Goal:
- Store each user's primary administrative area.

Expected fields:
- `governorate_id`
- `district_id`
- `address_details`

Expected updates:
- Customer model and schemas.
- Technician model and schemas.
- Customer profile response/update.
- Technician profile response/update.

### Task 3 - Update customer registration and profile
Status: Pending.

Goal:
- Let customers provide or update their governorate/district.

Expected updates:
- `POST /api/auth/register/customer`
- `GET /api/customer/profile/me`
- `PUT /api/customer/profile/me`

### Task 4 - Add technician service areas
Status: Pending.

Goal:
- Let technicians serve one or more areas.

Expected changes:
- Add `technician_service_areas` table.
- Allow district-level service areas.
- Allow governorate-level service areas when `district_id` is empty.
- Add technician profile endpoint for managing service areas.

### Task 5 - Store request and rating area context
Status: Pending.

Goal:
- Make ratings searchable by area.

Expected changes:
- Add `governorate_id` and `district_id` to requests.
- Add `request_id` to ratings.
- Store the request area when the customer creates a request.
- Use request-linked ratings to calculate area-specific reputation.

### Task 6 - Add top technicians endpoint
Status: Pending.

Goal:
- Return multiple highly rated technicians for a service and area.

Expected endpoint:
- `GET /api/technicians/top`

Expected behavior:
- Include approved technicians only.
- Do not require live availability.
- Do not require fresh location.
- Rank by area match, ratings, comments, and reliability metrics.

### Task 7 - Return photos, ratings, and comments
Status: Pending.

Goal:
- Provide enough data for the frontend technician cards.

Expected response fields:
- public profile photo URL.
- average rating.
- total ratings.
- recent positive comments.
- services.
- governorate and district names.
- availability status for display only.

### Task 8 - Keep nearby matching separate
Status: Pending.

Goal:
- Avoid mixing browsing behavior with immediate assignment behavior.

Expected updates:
- Keep `/api/technicians/nearby` focused on available technicians with fresh location.
- Add `profile_photo_url` to `/api/technicians/nearby` for UI consistency.
- Do not remove location freshness checks from request assignment.

### Task 9 - Document frontend integration
Status: Pending.

Goal:
- Update frontend-facing API notes after implementation.

Expected documentation:
- Explain the difference between:
  - `/api/technicians/top` for browsing rated technicians.
  - `/api/technicians/nearby` for live nearby matching.
- Add request/response examples.
- Add frontend form requirements for governorate and district selection.
