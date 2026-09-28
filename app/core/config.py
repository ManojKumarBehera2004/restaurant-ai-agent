"""
Application Configuration Module.
Loads environment variables and provides centralized settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "AI Restaurant Support & Operations Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # LLM Settings
    # Supports "gemini" or "mock" (for testing/offline validation)
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 1024

    # Database Settings
    DATABASE_URL: str = "sqlite:///./data/restaurant_ops.db"

    # RAG Settings
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    RAG_COLLECTION_NAME: str = "restaurant_knowledge"
    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.65  # Minimum similarity score for grounded answers

    # Agent Limits
    MAX_AGENT_ITERATIONS: int = 5
    SESSION_TIMEOUT_MINUTES: int = 60

    # Guardrails & Security
    ENABLE_GUARDRAILS: bool = True
    ENABLE_INJECTION_DETECTION: bool = True
    STRICT_CUSTOMER_ISOLATION: bool = True

    # Observability
    LOG_LEVEL: str = "INFO"
    ENABLE_AUDIT_LOGGING: bool = True

    # Operational Diagnostic Flags (can be toggled via API or config for testing)
    SIMULATE_ORDER_SERVICE_OUTAGE: bool = False
    SIMULATE_LLM_TIMEOUT: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
