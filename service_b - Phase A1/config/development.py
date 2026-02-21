# config/development.py

from .settings import Settings


class DevelopmentSettings(Settings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    API_KEY_REQUIRED: bool = False

    # Development-specific overrides
    USE_DASK: bool = False
    ENABLE_ASYNC_PROCESSING: bool = True

    class Config(Settings.Config):
        env_file = ".env.development"
