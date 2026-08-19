# Fi Khedmtak

> An on-demand field service platform that connects customers with technicians through location-aware matching, real-time request tracking, notifications, and role-based management.

## Overview

Fi Khedmtak is a service marketplace backend built with FastAPI.

The platform allows customers to submit service requests by selecting a service, describing the problem, optionally attaching an image, and providing their location.

The backend then identifies and ranks eligible technicians based on location, rating, acceptance rate, completion rate, availability, working hours, and service area.

The project was developed as a graduation project and focuses on building a complete backend workflow rather than a simple CRUD application.

---

## How It Works

```text
Customer
   │
   │ Creates service request
   ▼
Request Processing
   │
   ├── Validate service and location
   ├── Find eligible technicians
   └── Rank technicians
   │
   ▼
Technician Assignment
   │
   ├── Accept
   │
   └── Reject / Timeout
          │
          ▼
      Reassignment
          │
          ▼
       Next Technician
          │
          ▼
     Service Completed
          │
          ▼
        Rating
```

---

## Key Features

### Customer

- OTP-based authentication
- Customer registration and login
- Create service requests
- Attach images and notes
- Select service types
- Provide service location
- Track request status
- Receive notifications
- Rate technicians after completed requests

### Technician

- OTP-based authentication
- Technician registration
- Document submission for account verification
- Manage profile and service areas
- Configure availability and working hours
- Update live location
- Receive service requests
- Accept or reject requests
- Complete service requests
- Submit service reports

### Admin

- Monitor platform statistics
- Manage users and technicians
- Review technician accounts and documents
- Approve or reject custom service requests
- Monitor service requests
- View ratings
- Update technician account status
- Send broadcast notifications

---

## Technician Matching System

One of the main components of Fi Khedmtak is its automated technician assignment system.

Instead of simply selecting the nearest technician, the backend first filters technicians based on multiple eligibility rules.

### Eligibility Rules

A technician may be excluded when:

- Their account is not approved.
- They are unavailable or on break.
- Their live location is missing or outdated.
- They do not provide the requested service.
- The request is outside their service area.
- The request is outside their configured service radius.
- They are outside their working hours or working days.
- They already have an active assignment.

### Technician Ranking

Eligible technicians are ranked using:

| Factor | Weight |
|---|---:|
| Distance | 50% |
| Average Rating | 25% |
| Acceptance Rate | 15% |
| Completion Rate | 10% |

The weights are configurable through environment variables.

### Automatic Reassignment

After a technician is assigned:

1. The technician receives the request.
2. A five-minute acceptance timeout starts.
3. If the technician accepts, the request continues normally.
4. If the technician rejects or the assignment times out, the system attempts to assign another eligible technician.
5. If no suitable technician is available, the request is cancelled and the customer is notified.

---

## Real-Time Features

The backend integrates Firebase services for communication and real-time updates.

### Firebase Cloud Messaging

Used for push notifications such as:

- New service requests
- Request acceptance
- Request completion
- Account approval or rejection
- Customer ratings
- No-technician notifications
- Admin broadcasts

### Firebase Realtime Database

Used for optional real-time synchronization of:

- Technician live locations
- Request state
- Request tracking

---

## Authentication & Authorization

The API uses:

- OTP-based phone authentication
- JWT access tokens
- Password hashing with bcrypt
- Role-based access control

Supported user roles:

```text
customer
technician
admin
```

Protected endpoints use authentication dependencies to verify the current user and restrict administrative operations.

---

## System Architecture

```text
┌─────────────────────┐
│    Mobile Client    │
│       Flutter       │
└──────────┬──────────┘
           │
           │ REST API
           ▼
┌─────────────────────────────┐
│        FastAPI Backend      │
│                             │
│  ┌─────────┐ ┌───────────┐ │
│  │  Auth   │ │ Requests  │ │
│  ├─────────┤ ├───────────┤ │
│  │ Services│ │ Assignment│ │
│  ├─────────┤ ├───────────┤ │
│  │ Profiles│ │   Admin   │ │
│  └─────────┘ └───────────┘ │
└──────────┬──────────┬───────┘
           │          │
           ▼          ▼
      ┌────────┐  ┌─────────────┐
      │ MySQL  │  │   Firebase  │
      │        │  │ FCM + RTDB  │
      └────────┘  └─────────────┘
```

---

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- MySQL
- PyMySQL

### Authentication & Security

- JWT
- bcrypt
- python-jose
- OTP authentication

### Real-Time & Notifications

- Firebase Admin SDK
- Firebase Cloud Messaging
- Firebase Realtime Database

### Other

- Pydantic
- python-multipart
- HTTPX
- python-dotenv

---

## Project Structure

```text
app/
├── api/
│   ├── admin.py
│   ├── auth.py
│   ├── dependencies.py
│   ├── notifications.py
│   ├── requests.py
│   ├── services.py
│   ├── technician_profile.py
│   └── technicians.py
│
├── models/
│   ├── customer.py
│   ├── notification.py
│   ├── otp.py
│   ├── rating.py
│   ├── request.py
│   ├── request_assignment.py
│   ├── review.py
│   ├── service.py
│   └── technician.py
│
├── schemas/
│
├── services/
│   ├── assignment_service.py
│   ├── auth_service.py
│   ├── firebase_service.py
│   └── sms_service.py
│
├── config.py
└── database.py

main.py
requirements.txt
```

---

## Database

The backend uses MySQL with SQLAlchemy ORM.

Main entities include:

- Customers
- Technicians
- Services
- Service Categories
- Technician Services
- Technician Service Areas
- Service Requests
- Request Services
- Request Assignments
- Ratings
- Reviews
- Notifications
- OTP Verifications
- Governorates
- Districts

The `RequestAssignment` model keeps track of technician assignment attempts, including accepted, rejected, timeout, and cancelled states.

---

## API

The backend exposes RESTful endpoints grouped by functionality:

```text
/api/auth
/api/services
/api/locations
/api/requests
/api/technicians
/api/notifications
/api/customer/profile
/api/technician/profile
/api/admin
```

FastAPI automatically provides interactive API documentation:

```text
/docs
/redoc
```

When running locally:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/aziz758/backend_fikh.git
cd backend_fikh
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

#### Windows

```bash
copy .env.example .env
```

Update the required database and authentication settings.

### 5. Run the API

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

---

## Environment Variables

### Required

```env
DATABASE_URL=
SECRET_KEY=
```

### Optional

```env
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

SMS_API_URL=
SMS_API_KEY=

FIREBASE_CREDENTIALS_PATH=firebase_credentials.json
FIREBASE_DATABASE_URL=

TECHNICIAN_WORKING_HOURS_TIMEZONE=Asia/Riyadh

TECHNICIAN_LOCATION_TTL_MINUTES=5
TECHNICIAN_MAX_SERVICE_DISTANCE_KM=20

TECHNICIAN_PRIORITY_DISTANCE_WEIGHT=0.5
TECHNICIAN_PRIORITY_RATING_WEIGHT=0.25
TECHNICIAN_PRIORITY_ACCEPTANCE_WEIGHT=0.15
TECHNICIAN_PRIORITY_COMPLETION_WEIGHT=0.1
```

> Never commit `.env` or Firebase credentials to the repository.

---

## Request Status

### Request

```text
pending
   ↓
assigned
   ↓
accepted
   ↓
completed
```

A request may also become:

```text
cancelled
```

### Assignment

```text
pending
   ├── accepted
   ├── rejected
   └── timeout
```

---

## Current Limitations

The current version is a graduation-project MVP.

Known limitations include:

- Manual database migration scripts instead of Alembic.
- Limited automated test coverage.
- Some endpoints still use flexible payload structures.
- Firebase Realtime Database security hardening is not fully configured.

These areas can be improved for a production deployment.

---

## Project Status

**Graduation Project — MVP**

The backend is functional and was developed to support the customer, technician, and admin workflows of the Fi Khedmtak platform.

---

## Author

**Aziz Mohammed Abduljabbar Saad Al-maqtari**

GitHub: [@aziz758](https://github.com/aziz758)