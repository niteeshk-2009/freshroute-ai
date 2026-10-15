"""Configuration settings for FreshRoute AI backend."""

from __future__ import annotations

import os


class Settings:
    """Application settings loaded from environment variables."""
    HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./freshroute.db")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    APP_NAME: str = "FreshRoute AI"
    PROJECT_NAME: str = "FreshRoute AI"
    APP_VERSION: str = "1.0.0"
    VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Intelligent Decision Support for Perishable Produce Distribution"
    API_V1_STR: str = "/api"
    DEFAULT_SEED: int = 42


settings = Settings()
