"""Run this file to create all tables when the database exists but is empty."""
from app.database import engine, Base
from app.models import *  # noqa

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")
