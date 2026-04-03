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


settings = Settings()
