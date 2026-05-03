from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro-latest"

    # Conversion & processing limits
    max_upload_mb: int = 10
    max_pages: int = 20
    max_image_bytes: int = 4_000_000  # ~4MB per rendered page for safety

    # Timeouts (seconds)
    conversion_timeout_s: int = 45
    gemini_timeout_s: int = 60

    # Retry / circuit breaker
    gemini_retry_max_attempts: int = 3
    gemini_retry_base_delay_s: float = 1.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_reset_timeout_s: int = 60

    # Concurrency
    max_concurrent_requests: int = 3
    max_concurrent_gemini_calls: int = 2

    # Rate limit (in-memory, future scope: redis)
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60

    # CORS
    cors_allowed_origins: str = "*"  # comma-separated, or "*"


settings = Settings()

