import os
from pathlib import Path


def _load_env_file() -> None:
    """
    Load key=value pairs from a .env file (project root) into os.environ.
    Uses python-dotenv if available; otherwise falls back to a tiny parser.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"

    try:
        from dotenv import load_dotenv  # type: ignore

        # Load from project root explicitly so subprocess/reload modes are stable.
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()
    except Exception:
        pass

    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Do not override already-set environment variables
        os.environ.setdefault(key, value)


_load_env_file()


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    try:
        return float(v)
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL must be set in .env")
        self.DATABASE_URL: str = database_url

        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be set in .env")
        self.SECRET_KEY: str = secret_key
        self.ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            10080,  # 7 days
        )
        self.SMS_API_URL: str = os.getenv("SMS_API_URL", "")
        self.SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
        self.FIREBASE_CREDENTIALS_PATH: str = os.getenv(
            "FIREBASE_CREDENTIALS_PATH",
            "firebase_credentials.json",
        )
        self.FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "").strip()
        self.TECHNICIAN_WORKING_HOURS_TIMEZONE: str = os.getenv(
            "TECHNICIAN_WORKING_HOURS_TIMEZONE",
            "Asia/Riyadh",
        )
        self.TECHNICIAN_LOCATION_TTL_MINUTES: int = max(
            1,
            _get_int("TECHNICIAN_LOCATION_TTL_MINUTES", 5),
        )
        self.TECHNICIAN_MAX_SERVICE_DISTANCE_KM: float = max(
            1.0,
            _get_float("TECHNICIAN_MAX_SERVICE_DISTANCE_KM", 20.0),
        )
        self.TECHNICIAN_PRIORITY_DISTANCE_WEIGHT: float = max(
            0.0,
            _get_float("TECHNICIAN_PRIORITY_DISTANCE_WEIGHT", 0.5),
        )
        self.TECHNICIAN_PRIORITY_RATING_WEIGHT: float = max(
            0.0,
            _get_float("TECHNICIAN_PRIORITY_RATING_WEIGHT", 0.25),
        )
        self.TECHNICIAN_PRIORITY_ACCEPTANCE_WEIGHT: float = max(
            0.0,
            _get_float("TECHNICIAN_PRIORITY_ACCEPTANCE_WEIGHT", 0.15),
        )
        self.TECHNICIAN_PRIORITY_COMPLETION_WEIGHT: float = max(
            0.0,
            _get_float("TECHNICIAN_PRIORITY_COMPLETION_WEIGHT", 0.1),
        )


settings = Settings()
