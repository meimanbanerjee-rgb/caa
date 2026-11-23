# backend/app/config.py
# Loads application configuration and environment variables from .env.
# This is the single source of truth for secrets and runtime settings.

from pathlib import Path
from typing import List
import os
from dotenv import load_dotenv

# Find .env at project root or current working directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Settings:
    """Central configuration class for InsightForge AI."""

    def __init__(self) -> None:
        self.app_name: str = "InsightForge AI"
        self.version: str = "1.0.0"

        # AI Provider settings (Optional)
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
        self.llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
        self.llm_model: str = os.getenv("LLM_MODEL", "gemini-1.5-flash").strip()

        # Upload and limits
        self.max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
        self.max_upload_bytes: int = self.max_upload_mb * 1024 * 1024

        # Allowed CORS origins
        origins_raw = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
        )
        self.allowed_origins: List[str] = [
            origin.strip() for origin in origins_raw.split(",") if origin.strip()
        ]

        # Storage and Retention
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./insightforge.db")
        self.upload_retention_days: int = int(os.getenv("UPLOAD_RETENTION_DAYS", "7"))

        # Server
        self.host: str = os.getenv("HOST", "127.0.0.1")
        self.port: int = int(os.getenv("PORT", "8000"))

        # Base directories
        self.storage_dir: Path = ROOT_DIR / "backend" / "data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir: Path = self.storage_dir / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_ai_configured(self) -> bool:
        """Returns True only if an active AI key has been provided and provider is not 'none'."""
        return bool(self.llm_api_key and self.llm_provider != "none")


settings = Settings()
