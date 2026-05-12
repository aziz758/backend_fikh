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
- `technician_service_areas`
- `technician_service_requests`
- `service_categories`
- `services`
- `requests`
- `request_services`
- `request_assignments`
- `ratings`
- `reviews`
- `otp_verifications`
- `notifications`
- `governorates`
- `districts`

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
- `GET /grouped`
  - returns active services grouped by category for frontend display.
  - request creation still uses `service_id`; categories are display-only.

### Locations (`/api/locations`)
- `GET /governorates`
  - query: `include_inactive` optional, default `false`
- `GET /districts`
  - query: `governorate_id`, optional `include_inactive` default `false`

### Technicians (`/api/technicians`)
- `GET /top`
  - query: `service_id`, optional `governorate_id`, optional `district_id`, optional `limit`
  - returns approved technicians ranked for browsing by area reputation.
  - does not require technician availability or fresh live location.
- `GET /nearby`
  - query: `service_id`, `customer_lat`, `customer_lng`, optional `max_distance_km`
  - returns only available technicians with fresh live location and now includes `profile_photo_url`.

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
- `PUT /area`
- `GET /service-areas`
- `PUT /service-areas`
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
- `GET /technicians/{technician_id}`
- `PUT /custom-service-requests/{service_request_id}/approve`
- `PUT /custom-service-requests/{service_request_id}/reject`
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
python migrate_v9_locations.py
python migrate_v10_user_area_fields.py
python migrate_v11_technician_service_areas.py
python migrate_v12_request_rating_area_context.py
python migrate_v13_technician_service_requests.py
python migrate_v14_customer_profile_photo.py
python migrate_v15_service_categories.py
python seed_services.py
python seed_locations.py
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

Full frontend integration guide:
- [`docs/frontend-integration.md`](docs/frontend-integration.md)

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
  "registration_token": "...",
  "governorate_id": 4,
  "district_id": 28,
  "address_details": "Near the main street"
}
```

Customer area fields are optional during rollout, but if `district_id` is sent then `governorate_id` must also be sent and the district must belong to that governorate.

`POST /api/auth/register/technician` now requires:
```json
{
  "name": "Technician Name",
  "phone": "0501234567",
  "password": "secret123",
  "registration_token": "...",
  "service_ids": [1, 2],
  "custom_service_name": "تركيب وصيانة أبواب زجاج"
}
```

`custom_service_name` is optional. If sent, it creates a pending admin-review request and does not appear to customers until the admin approves and links it to an official service.

### Custom technician services
This section covers the frontend flow for the technician `أخرى` option.

Technician registration UI:
- Show `أخرى` as a frontend-only option when the technician cannot find their service.
- Do not send `أخرى` as a `service_id`.
- If the technician selects `أخرى`, show a required text input for the custom service name.
- Send the entered value as `custom_service_name`.
- `other_service_name` is accepted as a compatibility alias, but new frontend code should use `custom_service_name`.

Registration payload with an official service and a custom service request:
```json
{
  "name": "Technician Name",
  "phone": "0501234567",
  "password": "secret123",
  "registration_token": "...",
  "service_ids": [1],
  "custom_service_name": "تصليح ابواب زجاج"
}
```

Important customer-facing rule:
- The raw `custom_service_name` is hidden from customers.
- It is not added to `services`.
- It is not linked to the technician until admin review.
- After admin approval, customers only see the official service name from `services`.

Admin technician review data:
- `GET /api/admin/technicians`
- `GET /api/admin/technicians/{technician_id}`
- `GET /api/admin/dashboard`

Admin technician responses include:
```json
{
  "id": 10,
  "name": "Technician Name",
  "status": "pending_approval",
  "services": ["Electrician"],
  "pending_custom_service_requests_count": 1,
  "custom_service_requests": [
    {
      "id": 7,
      "requested_name": "تصليح ابواب زجاج",
      "status": "pending",
      "approved_service_id": null,
      "approved_service_name": "",
      "admin_note": "",
      "created_at": "2026-04-30 10:00:00",
      "reviewed_at": ""
    }
  ]
}
```

Recommended admin UI states:
- `pending`: show approve/reject actions.
- `approved`: show the official approved service name and disable review actions.
- `rejected`: show the rejection note and disable review actions.
- If `pending_custom_service_requests_count > 0`, show a visible review-required state before the account approval button.

Approve by linking to an existing official service:
```http
PUT /api/admin/custom-service-requests/7/approve
```

```json
{
  "service_id": 1,
  "admin_note": "Linked to existing electrician service"
}
```

Approve by creating or reusing a cleaner official service name:
```http
PUT /api/admin/custom-service-requests/7/approve
```

```json
{
  "service_name": "تركيب وصيانة أبواب زجاج",
  "admin_note": "Normalized technician wording"
}
```

Reject:
```http
PUT /api/admin/custom-service-requests/7/reject
```

```json
{
  "admin_note": "Service is not supported right now"
}
```

Review response shape:
```json
{
  "id": 7,
  "requested_name": "تصليح ابواب زجاج",
  "status": "approved",
  "approved_service_id": 12,
  "approved_service_name": "تركيب وصيانة أبواب زجاج",
  "admin_note": "Normalized technician wording",
  "created_at": "2026-04-30 10:00:00",
  "reviewed_at": "2026-04-30 10:05:00"
}
```

Technician account approval gate:
- `PUT /api/admin/technicians/{technician_id}/status` with `status = approved` returns `400` if the technician still has pending custom service requests.
- The frontend should handle this as a review-required error, not a generic failure.

Error response:
```json
{
  "detail": "Review pending custom service requests before approving technician"
}
```

Recommended frontend sequence for admin approval:
- Open technician review details.
- Review all `custom_service_requests` with `status = pending`.
- Approve each one by selecting an existing service or entering a clean official service name.
- Reject unsupported services with a clear note.
- Refresh the technician detail.
- Approve the technician account only after `pending_custom_service_requests_count` is `0`.

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

### Locations and area selection
Use these endpoints to populate governorate and district selectors:

`GET /api/locations/governorates`
```json
[
  {
    "id": 4,
    "name_ar": "تعز",
    "name_en": "Taiz",
    "is_active": true
  }
]
```

`GET /api/locations/districts?governorate_id=4`
```json
[
  {
    "id": 28,
    "governorate_id": 4,
    "name_ar": "القاهرة",
    "name_en": "Al Qahirah",
    "is_active": true
  }
]
```

Frontend rules:
- Load governorates first.
- After the user picks a governorate, load districts using `governorate_id`.
- If `district_id` is sent, `governorate_id` must also be sent.
- The backend rejects mismatched governorate/district pairs with `400`.

### Customer area fields
Customer registration can now send area fields:
```json
{
  "name": "Customer Name",
  "phone": "0501234567",
  "password": "secret123",
  "registration_token": "...",
  "governorate_id": 4,
  "district_id": 28,
  "address_details": "Near the main street"
}
```

Customer profile response now includes:
- `governorate_id`
- `governorate_name`
- `district_id`
- `district_name`
- `address_details`

Customer profile update:
- `PUT /api/customer/profile/me`
- Area fields are optional, but at least one field must be sent.

### Technician primary area and service areas
Technician primary area:
- `PUT /api/technician/profile/area`

Request:
```json
{
  "governorate_id": 4,
  "district_id": 28,
  "address_details": "Workshop address or landmark"
}
```

Technician service areas:
- `GET /api/technician/profile/service-areas`
- `PUT /api/technician/profile/service-areas`

Request:
```json
{
  "service_areas": [
    {
      "governorate_id": 4,
      "district_id": null
    },
    {
      "governorate_id": 2,
      "district_id": 15
    }
  ]
}
```

Meaning:
- `district_id: null` means the technician serves the full governorate.
- A concrete `district_id` means the technician serves that specific district only.
- Do not send a full-governorate area and district-level areas for the same governorate together.

### Technician browsing vs live nearby matching
Use two different screens/flows:

`GET /api/technicians/top`:
- Use this when the customer taps a service like `كهربائي` and wants to browse multiple highly rated technicians.
- Shows approved technicians even if they are offline.
- Does not require fresh live location.
- Ranks by area match, ratings, positive comments, completion rate, and acceptance rate.
- Good for a directory/listing screen.

Query:
```http
GET /api/technicians/top?service_id=1&governorate_id=4&district_id=28&limit=20
```

Response shape:
```json
{
  "results": [
    {
      "id": 2,
      "name": "Ahmed",
      "phone": "0501234567",
      "status": "approved",
      "availability_status": "offline",
      "profile_photo_url": "/uploads/technician_profiles/example.jpg",
      "services": [
        {
          "id": 1,
          "name": "كهربائي"
        }
      ],
      "governorate_id": 4,
      "governorate_name": "تعز",
      "district_id": 28,
      "district_name": "القاهرة",
      "address_details": "Near the main street",
      "avg_rating": 4.5,
      "total_ratings": 2,
      "area_avg_rating": 4.8,
      "area_total_ratings": 5,
      "positive_comment_count": 3,
      "positive_comments_scope": "area",
      "positive_comments": [
        {
          "id": 12,
          "request_id": 44,
          "score": 5.0,
          "comment": "فني ممتاز وسريع",
          "created_at": "2026-04-28T10:00:00"
        }
      ],
      "area_match": "service_district",
      "acceptance_rate": 0.8,
      "completion_rate": 0.9,
      "ranking_score": 340.15
    }
  ],
  "total": 1,
  "limit": 20
}
```

`positive_comments_scope`:
- `area`: comments are from ratings linked to requests in the selected area.
- `global`: comments are general technician comments, usually because old ratings are not area-linked yet.

`GET /api/technicians/nearby`:
- Use this only for immediate/live matching flows.
- Requires the technician to be approved, available, inside distance, inside work hours, without active accepted request, and with fresh `lat/lng`.
- Now includes `profile_photo_url`, but the strict matching rules are unchanged.

Query:
```http
GET /api/technicians/nearby?service_id=1&customer_lat=14.8282&customer_lng=42.9700
```

### Request area context
`POST /api/requests/` now accepts optional area fields:
```json
{
  "service_ids": [1],
  "note": "Need electrical repair",
  "lat": 14.8282,
  "lng": 42.97,
  "address": "Customer selected map address",
  "governorate_id": 4,
  "district_id": 28
}
```

If the request does not send `governorate_id` and `district_id`, the backend uses the customer's saved area when available.

Request responses include:
- `governorate_id`
- `governorate_name`
- `district_id`
- `district_name`

Ratings submitted through `POST /api/requests/{request_id}/rate` are linked to the request, which lets `/api/technicians/top` calculate area-specific reputation over time.

### Backend deployment note for frontend testing
Before testing the new frontend flows on an existing database, run:
```bash
python migrate_v8_otp_hash.py
python migrate_v9_locations.py
python migrate_v10_user_area_fields.py
python migrate_v11_technician_service_areas.py
python migrate_v12_request_rating_area_context.py
python seed_locations.py
```

Without these migrations, OTP hashing, area selectors, technician service areas, and area-linked ratings may not work correctly.

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
- Continue with Task 2.

### Task 1 - Add governorates and districts
Status: Done.

Goal:
- Add stable administrative location tables for customers, technicians, and requests.

Completed:
- Add `Governorate` model.
- Add `District` model.
- Add `migrate_v9_locations.py`.
- Add `seed_locations.py` with initial Yemeni governorates and common districts.
- Add location list endpoints:
  - `GET /api/locations/governorates`
  - `GET /api/locations/districts?governorate_id=...`

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Run `python migrate_v9_locations.py` successfully.
- Run `python seed_locations.py` successfully; seeded `22` governorates and `162` districts in the current development database.
- Verify `GET /api/locations/governorates` returns `200`.
- Verify `GET /api/locations/districts?governorate_id=...` returns `200`.

Remaining:
- Continue with Task 3.

### Task 2 - Add area fields to customers and technicians
Status: Done.

Goal:
- Store each user's primary administrative area.

Completed fields:
- `governorate_id`
- `district_id`
- `address_details`

Completed updates:
- Customer model and schemas.
- Technician model and schemas.
- Customer profile response/update.
- Technician profile response/update.
- Added `migrate_v10_user_area_fields.py`.
- Added area validation so a district must belong to the selected governorate.
- Added technician primary area update endpoint:
  - `PUT /api/technician/profile/area`

Validation:
- Run `python migrate_v10_user_area_fields.py` successfully.
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify customer profile serialization includes area fields.
- Verify technician profile serialization includes area fields.
- Verify invalid district/governorate combinations return `400`.

Remaining:
- Task 3 still needs to let customer registration submit the area during account creation.
- Task 4 still needs technician service areas for serving multiple governorates/districts.

### Task 3 - Update customer registration and profile
Status: Done.

Goal:
- Let customers provide or update their governorate/district.

Completed:
- `POST /api/auth/register/customer` now accepts optional area fields:
  - `governorate_id`
  - `district_id`
  - `address_details`
- Customer registration validates that the district belongs to the selected governorate.
- `GET /api/customer/profile/me` returns the customer's area fields and names.
- `PUT /api/customer/profile/me` updates the customer's area fields.
- The new registration fields are optional to keep old frontend clients working during rollout.

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify `CustomerCreate` accepts optional area fields.
- Verify invalid district/governorate combinations return `400`.

Remaining:
- Continue with Task 5.

### Task 4 - Add technician service areas
Status: Done.

Goal:
- Let technicians serve one or more areas.

Completed:
- Add `technician_service_areas` table.
- Allow district-level service areas.
- Allow governorate-level service areas when `district_id` is empty.
- Add `migrate_v11_technician_service_areas.py`.
- Add technician profile endpoints for managing service areas:
  - `GET /api/technician/profile/service-areas`
  - `PUT /api/technician/profile/service-areas`
- The `PUT` endpoint replaces the technician's full service-area list.
- Duplicate service areas are rejected.
- A governorate-level service area cannot be combined with district-level areas in the same governorate.

Example `PUT /api/technician/profile/service-areas` request:
```json
{
  "service_areas": [
    {
      "governorate_id": 4,
      "district_id": null
    },
    {
      "governorate_id": 2,
      "district_id": 15
    }
  ]
}
```

Response:
```json
[
  {
    "id": 1,
    "governorate_id": 4,
    "governorate_name": "تعز",
    "district_id": null,
    "district_name": null,
    "scope": "governorate"
  }
]
```

Validation:
- Run `python migrate_v11_technician_service_areas.py` successfully.
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify service-area routes exist.
- Verify service-area validation rejects duplicates and overlapping governorate/district scopes.

Remaining:
- Continue with Task 6.

### Task 5 - Store request and rating area context
Status: Done.

Goal:
- Make ratings searchable by area.

Completed:
- Add `governorate_id` and `district_id` to requests.
- Add `request_id` to ratings.
- Store the request area when the customer creates a request.
- Add `migrate_v12_request_rating_area_context.py`.
- Request create accepts optional area fields:
  - `governorate_id`
  - `district_id`
- If the request does not include area fields, the backend uses the customer's saved area.
- Request responses now include:
  - `governorate_id`
  - `governorate_name`
  - `district_id`
  - `district_name`
- Ratings created through `POST /api/requests/{request_id}/rate` now store `request_id`.

Validation:
- Run `python migrate_v12_request_rating_area_context.py` successfully.
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify `RequestCreate` accepts optional area fields.
- Verify request response serialization includes area fields.
- Verify new rating rows can link back to the rated request.

Remaining:
- Task 6 still needs to calculate and expose area-specific technician reputation in `/api/technicians/top`.

### Task 6 - Add top technicians endpoint
Status: Done.

Goal:
- Return multiple highly rated technicians for a service and area.

Completed endpoint:
- `GET /api/technicians/top`

Completed behavior:
- Include approved technicians only.
- Do not require live availability.
- Do not require fresh location.
- Rank by area match, ratings, comments, and reliability metrics.
- Supports optional area filters:
  - `governorate_id`
  - `district_id`
- Matches technicians by their primary area or `technician_service_areas`.
- Returns a paginated-style object:
```json
{
  "results": [
    {
      "id": 2,
      "name": "Ahmed",
      "status": "approved",
      "availability_status": "offline",
      "profile_photo_url": "/uploads/technician_profiles/example.jpg",
      "services": [
        {
          "id": 1,
          "name": "كهربائي"
        }
      ],
      "governorate_id": 4,
      "governorate_name": "تعز",
      "district_id": 28,
      "district_name": "القاهرة",
      "avg_rating": 4.5,
      "total_ratings": 2,
      "area_avg_rating": 0.0,
      "area_total_ratings": 0,
      "positive_comment_count": 1,
      "positive_comments_scope": "global",
      "positive_comments": [
        {
          "id": 12,
          "request_id": 44,
          "score": 5.0,
          "comment": "فني ممتاز وسريع",
          "created_at": "2026-04-28T10:00:00"
        }
      ],
      "area_match": "service_governorate",
      "acceptance_rate": 0.8,
      "completion_rate": 0.9,
      "ranking_score": 240.15
    }
  ],
  "total": 1,
  "limit": 20
}
```

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify `GET /api/technicians/top?service_id=...` returns `200`.
- Verify invalid area combinations return `400`.

Remaining:
- Continue with Task 8.

### Task 7 - Return photos, ratings, and comments
Status: Done.

Goal:
- Provide enough data for the frontend technician cards.

Completed response fields in `GET /api/technicians/top`:
- `profile_photo_url`: public technician profile image URL.
- `services`: service IDs and names for the technician.
- `avg_rating`: global average rating.
- `total_ratings`: global rating count.
- `area_avg_rating`: area-specific average rating when area-linked ratings exist.
- `area_total_ratings`: area-specific rating count.
- `positive_comment_count`: count used for ranking.
- `positive_comments`: latest positive comments.
- `positive_comments_scope`: `area` when comments are area-specific, otherwise `global`.
- `governorate_name` and `district_name`.
- `availability_status` for display only.

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify `GET /api/technicians/top?service_id=...` includes:
  - `profile_photo_url`
  - `services`
  - `positive_comments`
  - `positive_comments_scope`

Remaining:
- Continue with Task 9.

### Task 8 - Keep nearby matching separate
Status: Done.

Goal:
- Avoid mixing browsing behavior with immediate assignment behavior.

Completed:
- Keep `/api/technicians/nearby` focused on available technicians with fresh location.
- Add `profile_photo_url` to `/api/technicians/nearby` for UI consistency.
- Do not remove location freshness checks from request assignment.
- Did not change availability, distance, work-hours, active-request, or freshness filters.

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify `profile_photo_url` is present in the nearby response builder.
- Verify `GET /api/technicians/nearby` still returns `200` with the current strict filters.

Remaining:
- The top-technicians by area plan is complete.

### Task 9 - Document frontend integration
Status: Done.

Goal:
- Update frontend-facing API notes after implementation.

Completed:
- Explain the difference between:
  - `/api/technicians/top` for browsing rated technicians.
  - `/api/technicians/nearby` for live nearby matching.
- Add request/response examples.
- Add frontend form requirements for governorate and district selection.
- Document location selector endpoints.
- Document customer area fields.
- Document technician primary area and service-area endpoints.
- Document request area context and area-linked ratings.
- Document the required deployment migrations and seed command.

Validation:
- README contains frontend integration notes for the full area workflow.
- README contains examples for `/api/locations`, `/api/technicians/top`, `/api/technicians/nearby`, and `POST /api/requests/`.

Remaining:
- Add API-level automated tests for the new area and top-technician flows.

---

## 15. Technician Custom Service Review Plan
This plan tracks the workflow for technicians who offer a service that is not yet available in the official `services` list.

### Product behavior
- The technician can choose `أخرى` when their service is not listed.
- The technician writes the service name they provide.
- The service name written by the technician does not appear to customers immediately.
- The technician waits for admin review during the normal document/account approval flow.
- The admin reviews the requested service name before approving or rejecting it.
- The admin can rewrite the service into a cleaner official name, link it to an existing service, or reject it.
- Only approved official services are linked to the technician and shown to customers.

### Why this flow is needed
- Technicians may write unclear, duplicated, or unprofessional service names.
- Admin review keeps the service catalog clean.
- Multiple technician requests can be normalized into one official service.
- Customer-facing categories stay consistent and searchable.

### Proposed data model
Add a review table:

```text
technician_service_requests
- id
- technician_id
- requested_name
- status: pending / approved / rejected
- approved_service_id
- admin_note
- created_at
- reviewed_at
```

Recommended behavior:
- `requested_name` stores the raw name entered by the technician.
- `approved_service_id` points to the official service selected or created by the admin.
- `status = pending` means the admin has not reviewed it yet.
- `status = approved` means the technician was linked to an official service.
- `status = rejected` means the requested service will not be used.

### Admin review options
When reviewing a technician, the admin should be able to:
- link the request to an existing official service.
- create a new official service with a clean name, then link the technician to it.
- reject the request with a note.

Example:
- Technician writes: `تصليح ابواب زجاج`
- Admin approves official service as: `تركيب وصيانة أبواب زجاج`
- Backend creates or selects that official service.
- Backend links the technician to the official service through `technician_services`.

### Approval rule recommendation
Before setting a technician to `approved`:
- if the technician has pending custom service requests, the admin should review them first.
- after review, rejected requests do not block approval.
- approved requests link the technician to official services.

This prevents a technician from being approved while their main custom service is still unresolved.

### Task 10 - Document the custom service review plan
Status: Done.

Completed:
- Added this plan to define the custom-service workflow before changing code.
- Clarified that technician-entered service names remain hidden from customers until admin approval.
- Clarified admin options for linking, creating, or rejecting service requests.

Remaining:
- Continue with Task 12.

### Task 11 - Add technician service request table
Status: Done.

Goal:
- Store custom service names requested by technicians.

Completed:
- Add `TechnicianServiceRequest` model.
- Add `migrate_v13_technician_service_requests.py`.
- Add statuses:
  - `pending`
  - `approved`
  - `rejected`
- Add relation to `technicians`.
- Add optional relation to approved `services`.
- Add table `technician_service_requests` with:
  - `technician_id`
  - `requested_name`
  - `status`
  - `approved_service_id`
  - `admin_note`
  - `created_at`
  - `reviewed_at`

Validation:
- Run `python migrate_v13_technician_service_requests.py` successfully.
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify the model is available from `app.models`.
- Existing technicians and services are unaffected.

Remaining:
- Task 12 still needs to allow technician registration to create pending custom service requests.

### Task 12 - Allow technician registration with custom service name
Status: Done.

Goal:
- Let technicians submit a service name when their service is not listed.

Completed:
- Add optional `custom_service_name` to technician registration schema.
- Add `other_service_name` as a compatibility alias.
- Trim and validate the custom service name.
- If the technician sends a custom service name, create a `pending` `TechnicianServiceRequest`.
- The custom service is not added to `services`.
- The custom service is not linked through `technician_services`.
- The custom service remains hidden from customers until admin review in later tasks.

Validation:
- Registration works without a custom service.
- Registration with a custom service creates a pending service request.
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify `TechnicianCreate` accepts and normalizes custom service names.
- Verify conflicting `custom_service_name` and `other_service_name` are rejected.
- Verify `POST /api/auth/register/technician` creates a pending service request in a rolled-back transactional API check.

Remaining:
- Task 14 still needs to add admin approve/reject actions for custom service requests.

### Task 13 - Show custom service requests to admins
Status: Done.

Goal:
- Make admin review screens aware of pending custom service requests.

Completed:
- Include custom service requests in `GET /api/admin/technicians`.
- Include custom service requests in `GET /api/admin/dashboard` pending technician cards.
- Add admin technician detail endpoint:
  - `GET /api/admin/technicians/{technician_id}`
- Add `pending_custom_service_requests_count` to admin technician responses.
- Each custom service request includes:
  - `id`
  - `requested_name`
  - `status`
  - `approved_service_id`
  - `approved_service_name`
  - `admin_note`
  - `created_at`
  - `reviewed_at`

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify admin technician list, technician detail, and dashboard responses include pending custom service requests in a rolled-back transactional API check.

Remaining:
- Task 15 still needs to connect technician account approval with unresolved custom service requests.

### Task 14 - Add admin decision endpoints
Status: Done.

Goal:
- Let admins approve, normalize, or reject custom service requests.

Completed endpoints:
- `PUT /api/admin/custom-service-requests/{service_request_id}/approve`
- `PUT /api/admin/custom-service-requests/{service_request_id}/reject`

Approve by linking to an existing official service:
```json
{
  "service_id": 1,
  "admin_note": "Linked to existing electrician service"
}
```

Approve by creating or reusing a clean official service name:
```json
{
  "service_name": "تركيب وصيانة أبواب زجاج",
  "admin_note": "Normalized technician wording"
}
```

Reject:
```json
{
  "admin_note": "Service is not supported right now"
}
```

Completed behavior:
- Approval requires exactly one of `service_id` or `service_name`.
- If `service_id` is sent, the backend links the technician to that official service.
- If `service_name` is sent, the backend reuses an existing matching service name or creates a new official service.
- Approval creates the `technician_services` link only if it does not already exist.
- Approval updates the custom request to `status = approved`, stores `approved_service_id`, `admin_note`, and `reviewed_at`.
- Rejection updates the custom request to `status = rejected`, stores `admin_note` and `reviewed_at`, and does not create a service link.
- Already reviewed custom service requests cannot be reviewed again.
- Customer-facing service names still come from official `services`, not raw technician text.

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify approving with an existing service links the technician through `technician_services`.
- Verify approving with a new service name creates/reuses an official `services` row and links the technician.
- Verify rejecting keeps the request rejected and does not create a service link.
- Verify an already reviewed request returns `400`.

Remaining:
- Add API-level automated tests for the full custom service review flow.

### Task 15 - Connect technician approval with custom service review
Status: Done.

Goal:
- Keep technician approval consistent with pending custom service requests.

Completed behavior:
- `PUT /api/admin/technicians/{technician_id}/status` now blocks `status = approved` when the technician has pending custom service requests.
- The backend returns `400` with:
  - `Review pending custom service requests before approving technician`
- Approved or rejected custom service requests do not block technician approval.
- Other technician status changes, such as `rejected`, `pending_approval`, or `pending_documents`, are not blocked by pending custom service requests.

Validation:
- Import the FastAPI app successfully.
- Parse all Python files successfully.
- Verify a technician with a pending custom service request cannot be approved.
- Verify the same technician can be approved after the custom service request is approved or rejected.

Remaining:
- Add API-level automated tests for the full custom service review flow.

### Task 16 - Document frontend integration
Status: Done.

Goal:
- Document how frontend and admin UI should handle custom technician services.

Completed documentation:
- Technician registration payload with `custom_service_name`.
- How the frontend should handle the `أخرى` option.
- Admin review UI states for `pending`, `approved`, and `rejected` custom service requests.
- Admin approve/reject API actions.
- Approval with existing official service.
- Approval with a clean new official service name.
- Rejection with admin note.
- Technician account approval gate when custom service requests are still pending.
- Customer-facing behavior after approval.

Validation:
- README includes request/response examples for the custom service review flow.

Remaining:
- Add API-level automated tests for the full custom service review flow.
