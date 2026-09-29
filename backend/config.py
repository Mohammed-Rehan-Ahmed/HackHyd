"""
Configuration settings loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App
    APP_NAME: str = "Rural Healthcare Referral System"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./healthcare.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production-super-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TOKEN_EXPIRE", "60"))

    # Hindsight memory
    HINDSIGHT_API_URL: str = os.getenv("HINDSIGHT_API_URL", "http://localhost:8888")
    HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")

    # Groq LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    # Triage thresholds
    CRITICAL_SCORE_THRESHOLD: int = 8   # Score ≥ 8  → CRITICAL
    HIGH_SCORE_THRESHOLD: int = 5        # Score ≥ 5  → HIGH
    MEDIUM_SCORE_THRESHOLD: int = 3      # Score ≥ 3  → MEDIUM
    # Anything below → LOW

    # WebSocket ping interval (seconds)
    WS_PING_INTERVAL: int = 30

    # Notification settings
    NOTIFICATION_RETRY_ATTEMPTS: int = 3
    NOTIFICATION_RETRY_DELAY: int = 5  # seconds


settings = Settings()
