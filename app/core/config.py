"""
Core application configuration.

All settings are read from environment variables (or a .env file).
Pydantic-Settings handles parsing, validation, and type coercion automatically.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App metadata ──────────────────────────────────────────────────────
    APP_NAME: str = "Automated Report Generator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Server ────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Storage ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "/tmp/report_gen/uploads"
    OUTPUT_DIR: str = "/tmp/report_gen/outputs"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── CORS ──────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]


# Singleton — import this everywhere
settings = Settings()
