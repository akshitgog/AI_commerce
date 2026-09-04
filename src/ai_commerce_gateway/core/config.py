from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "AI Commerce Gateway"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_commerce_gateway"
    test_database_url: str | None = None
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: int = Field(default=30, ge=1)
    storage_provider: str = "unconfigured"
    storage_bucket: str = "product-images"
    storage_public_base_url: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: SecretStr | None = None
    razorpay_api_base_url: str = "https://api.razorpay.com"
    razorpay_timeout_seconds: float = Field(default=10.0, gt=0)
    razorpay_checkout_name: str = "AI Commerce Gateway"


@lru_cache
def get_settings() -> Settings:
    return Settings()
