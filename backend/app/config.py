"""Application settings, read from environment variables (.env supported)."""
import os
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (repo root or backend/) — avoids an extra dependency."""
    for candidate in (Path(__file__).resolve().parents[2] / ".env",
                      Path(__file__).resolve().parents[1] / ".env"):
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
            break


_load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./cma.db")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
