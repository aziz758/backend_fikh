import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, notifications, requests, services, technician_profile, technicians
from app.api.requests import upload_router
from app.database import engine, Base

app = FastAPI(title="Fi Khedmtak API", version="1.0")

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(requests.router, prefix="/api")
app.include_router(upload_router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(technicians.router, prefix="/api")
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(technician_profile.router, prefix="/api/technician/profile", tags=["Technician Profile"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
def root():
    return {"message": "Fi Khedmtak API", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Create tables automatically (if they do not exist).
# Note: if your MySQL database is already prepared, you do not need this.
# Base.metadata.create_all(bind=engine)
