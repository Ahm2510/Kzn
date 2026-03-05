# config/settings.py

from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=False)


def _get_cors_origins() -> List[str]:
    """Compute CORS_ORIGINS based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    
    if cors_origins_env:
        return [
            origin.strip() 
            for origin in cors_origins_env.split(",")
            if origin.strip()
        ]
    elif env == "development":
        # Only use localhost defaults in development mode
        return [
            "http://localhost:3000",
            "http://localhost:5500",
            "http://localhost:8080",
            "http://localhost:8081",
            "http://localhost:5173",
            "http://127.0.0.1:5500",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081",
            "http://127.0.0.1:56991",
            "http://127.0.0.1:8001"
        ]
    else:
        # Production/Docker: require explicit CORS_ORIGINS
        return []


class Settings(BaseModel):
    # ------------------------------------------------------------------
    # Service identity
    # ------------------------------------------------------------------
    SERVICE_NAME: str = "service_b"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # "json" or "plain"

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    BASE_DIR: Path = Path(__file__).resolve().parents[1]
    BASE_DATA_PATH: Path = Path(os.getenv("BASE_DATA_PATH", BASE_DIR / "data"))

    LOGS_PATH: Path = BASE_DATA_PATH / "logs"
    DATASETS_PATH: Path = BASE_DATA_PATH / "datasets"
    ENCODERS_PATH: Path = BASE_DATA_PATH / "encoders"
    TEMP_DIR: Path = BASE_DATA_PATH / "temp"
    MODELS_PATH: Path = BASE_DATA_PATH / "models"
    MODEL_REGISTRY_DB_PATH: Path = BASE_DATA_PATH / "model_registry.sqlite"
    VISUALIZATIONS_PATH: Path = BASE_DATA_PATH / "visualizations" 
    REPORTS_PATH: Path = BASE_DATA_PATH / "reports"


    # ------------------------------------------------------------------
    # Flags
    # ------------------------------------------------------------------
    DEBUG: bool = ENVIRONMENT != "production"
    API_KEY_REQUIRED: bool = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"

    # ------------------------------------------------------------------
    # Security settings
    # ------------------------------------------------------------------
    # CORS origins (comma-separated in env)
    # Defaults to localhost for development, but must be set explicitly in production/Docker
    CORS_ORIGINS: List[str] = _get_cors_origins()
    
    # Rate limiting (requests per minute)
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")
    ANALYZE_LIMIT: str = os.getenv("ANALYZE_LIMIT", "20/minute")  # Stricter for /v1/analyze
    RATE_LIMIT_ENABLED: bool = os.getenv(
        "RATE_LIMIT_ENABLED",
        "false" if ENVIRONMENT == "development" else "true",
    ).lower() == "true"
    
    # Internal endpoint authentication
    INTERNAL_SECRET: Optional[str] = os.getenv("INTERNAL_SECRET")
    ALLOW_INTERNAL_PUBLIC: bool = os.getenv("ALLOW_INTERNAL_PUBLIC", "false").lower() == "true"

    # ------------------------------------------------------------------
    # Validation constraints
    # ------------------------------------------------------------------
    SUPPORTED_FILE_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls", ".parquet", ".json"]
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "200000"))  # 200k default
    MAX_COLUMNS: int = int(os.getenv("MAX_COLUMNS", "1000"))
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "10"))  # 10MB default
    ALLOWED_WORKSPACES: Optional[List[str]] = None
    CELERY_BROKER_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def ensure_dirs(self) -> None:
        """
        Create base runtime directories required by the service.
        Safe to call multiple times (idempotent).
        """
        # Create base data folder and its well-known children
        self.BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.DATASETS_PATH.mkdir(parents=True, exist_ok=True)
        self.ENCODERS_PATH.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_PATH.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# Singleton instance exported for the rest of the app
# ------------------------------------------------------------------
settings = Settings()
