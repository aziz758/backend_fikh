from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, services, requests, technicians
from app.database import engine, Base

app = FastAPI(title="في خدمتك API", version="1.0")

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
app.include_router(technicians.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "في خدمتك API", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# إنشاء الجداول تلقائياً (إذا لم تكن موجودة)
# ملاحظة: إذا قاعدة البيانات جاهزة من MySQL فلا تحتاج هذا
# Base.metadata.create_all(bind=engine)
