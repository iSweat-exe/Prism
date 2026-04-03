from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings and configuration management using Pydantic.
    Environment variables can override these defaults (case-insensitive).
    """

    APP_NAME: str = "PrismAPI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Paths
    PROCFS_PATH: str = "/proc"

    # Infrastructure Service Names
    GATEWAY_NAME: str = "nginx-proxy"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "prism.log"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
