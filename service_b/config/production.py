# config/production.py

from .settings import Settings


class ProductionSettings(Settings):
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    API_KEY_REQUIRED: bool = True

    # Production-specific overrides
    USE_DASK: bool = True
    ENABLE_ASYNC_PROCESSING: bool = True

    class Config(Settings.Config):
        env_file = ".env.production"
