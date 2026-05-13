"""Run all manual database migrations in the correct order.

Usage:
  python run_migrations.py
  python run_migrations.py --with-seeds
"""
from __future__ import annotations

import argparse
import importlib
from collections.abc import Callable

from app import models  # noqa: F401 - register SQLAlchemy models
from app.database import Base, engine


MIGRATIONS: list[tuple[str, str]] = [
    ("migrate_requests_v2", "main"),
    ("migrate_v3", "migrate"),
    ("migrate_v4", "migrate"),
    ("migrate_v5", "migrate"),
    ("migrate_v6", "migrate"),
    ("migrate_v7", "migrate"),
    ("migrate_v8_otp_hash", "migrate"),
    ("migrate_v9_locations", "migrate"),
    ("migrate_v10_user_area_fields", "migrate"),
    ("migrate_v11_technician_service_areas", "migrate"),
    ("migrate_v12_request_rating_area_context", "migrate"),
    ("migrate_v13_technician_service_requests", "migrate"),
    ("migrate_v14_customer_profile_photo", "migrate"),
    ("migrate_v15_service_categories", "migrate"),
]

SEEDS: list[tuple[str, str]] = [
    ("seed_services", "seed"),
    ("seed_locations", "seed"),
]


def _load_callable(module_name: str, function_name: str) -> Callable[[], None]:
    module = importlib.import_module(module_name)
    fn = getattr(module, function_name, None)
    if not callable(fn):
        raise RuntimeError(f"{module_name}.{function_name} is not callable")
    return fn


def _run_step(module_name: str, function_name: str) -> None:
    print(f"\n=== Running {module_name}.{function_name} ===")
    fn = _load_callable(module_name, function_name)
    fn()


def run_migrations() -> None:
    print("=== Creating missing tables from current models ===")
    Base.metadata.create_all(bind=engine)
    print("Base tables are ready")

    for module_name, function_name in MIGRATIONS:
        _run_step(module_name, function_name)


def run_seeds() -> None:
    for module_name, function_name in SEEDS:
        _run_step(module_name, function_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all manual migrations.")
    parser.add_argument(
        "--with-seeds",
        action="store_true",
        help="Also seed services and locations after migrations.",
    )
    args = parser.parse_args()

    run_migrations()
    if args.with_seeds:
        run_seeds()

    print("\nDatabase migration run completed.")


if __name__ == "__main__":
    main()
