from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, Literal

import yaml
from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

CONFIG_FILE_ENV = "APP_CONFIG_FILE"
DEFAULT_CONFIG_PATH = Path("config/default.yaml")
LOCAL_CONFIG_NAME = "local.yaml"

_CONFIG_SCHEMA: dict[str, dict[str, str]] = {
    "app": {"environment": "app_env", "name": "app_name", "log_level": "log_level"},
    "database": {
        "url": "database_url",
        "test_url": "test_database_url",
        "pool_size": "db_pool_size",
        "max_overflow": "db_max_overflow",
        "pool_timeout_seconds": "db_pool_timeout_seconds",
    },
    "llm": {
        "provider": "llm_provider",
        "model": "llm_model",
        "api_key": "llm_api_key",
        "base_url": "llm_base_url",
        "temperature": "llm_temperature",
        "max_tool_steps": "llm_max_tool_steps",
    },
    "storage": {
        "provider": "storage_provider",
        "bucket": "storage_bucket",
        "public_base_url": "storage_public_base_url",
    },
    "razorpay": {
        "key_id": "razorpay_key_id",
        "key_secret": "razorpay_key_secret",
        "webhook_secret": "razorpay_webhook_secret",
        "api_base_url": "razorpay_api_base_url",
        "timeout_seconds": "razorpay_timeout_seconds",
        "checkout_name": "razorpay_checkout_name",
    },
    "buyer_sessions": {
        "secret": "buyer_sessions_secret",
        "issuer_key": "buyer_sessions_issuer_key",
        "ttl_seconds": "buyer_sessions_ttl_seconds",
    },
    "buyer_services": {
        "mode": "buyer_services_mode",
        "catalog_base_url": "buyer_services_catalog_base_url",
        "transaction_base_url": "buyer_services_transaction_base_url",
        "timeout_seconds": "buyer_services_timeout_seconds",
    },
    "merchant_mcp": {
        "api_base_url": "merchant_mcp_api_base_url",
        "timeout_seconds": "merchant_mcp_timeout_seconds",
        "publication_secret": "merchant_mcp_publication_secret",
        "publication_audience": "merchant_mcp_publication_audience",
        "confirmation_ttl_seconds": "merchant_mcp_confirmation_ttl_seconds",
    },
}


class Settings(BaseSettings):
    """Validated runtime settings loaded primarily from YAML configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "AI Commerce Gateway"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_commerce_gateway"
    test_database_url: str | None = None
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: int = Field(default=30, ge=1)

    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    llm_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("llm_api_key", "LLM_API_KEY", "FIREWORKS_API_KEY"),
    )
    llm_base_url: str | None = None
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_max_tool_steps: int = Field(default=8, ge=1, le=32)

    storage_provider: str = "unconfigured"
    storage_bucket: str = "product-images"
    storage_public_base_url: str | None = None
    # AWS S3 credentials
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    # GCP credentials (JSON string)
    gcp_credentials_json: SecretStr | None = None
    # Supabase credentials
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_anon_key: str | None = None

    razorpay_key_id: str | None = None
    razorpay_key_secret: SecretStr | None = None
    razorpay_webhook_secret: SecretStr | None = None
    razorpay_api_base_url: str = "https://api.razorpay.com"
    razorpay_timeout_seconds: float = Field(default=10.0, gt=0)
    razorpay_checkout_name: str = "AI Commerce Gateway"

    # When unset, an ephemeral per-process secret is generated: confirmation
    # tokens remain unforgeable but stop working at restart (dev semantics).
    buyer_services_mode: Literal["in_process", "remote"] = "in_process"
    buyer_services_catalog_base_url: str | None = None
    buyer_services_transaction_base_url: str | None = None
    buyer_services_timeout_seconds: float = Field(default=10.0, gt=0)

    buyer_sessions_secret: SecretStr | None = None
    buyer_sessions_issuer_key: SecretStr | None = None
    buyer_sessions_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    merchant_mcp_api_base_url: str | None = None
    merchant_mcp_timeout_seconds: float = Field(default=10.0, gt=0)
    merchant_mcp_publication_secret: SecretStr | None = None
    merchant_mcp_publication_audience: str = "merchant-mcp-publication"
    merchant_mcp_confirmation_ttl_seconds: int = Field(default=300, ge=1, le=300)

    @model_validator(mode="after")
    def _fill_ephemeral_publication_secret(self) -> Settings:
        """Dev semantics: one ephemeral secret per process when unconfigured."""
        if self.merchant_mcp_publication_secret is None:
            self.merchant_mcp_publication_secret = SecretStr(token_urlsafe(32))
        return self

    @property
    def publication_secret_value(self) -> str:
        """The publication-confirmation signing secret (always resolved)."""
        assert self.merchant_mcp_publication_secret is not None
        return self.merchant_mcp_publication_secret.get_secret_value()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_settings = InitSettingsSource(settings_cls, _load_yaml_settings())
        return init_settings, env_settings, dotenv_settings, yaml_settings, file_secret_settings


def _load_yaml_settings() -> dict[str, Any]:
    default_path = _resolve_default_config_path()
    explicit_path = os.getenv(CONFIG_FILE_ENV)

    merged: dict[str, Any] = {}
    if default_path.exists():
        merged = _read_yaml_mapping(default_path)
    elif explicit_path is None:
        raise FileNotFoundError(
            f"Default configuration file not found: {default_path}. "
            f"Create it or set {CONFIG_FILE_ENV}."
        )

    if explicit_path is not None:
        overlay_path = _resolve_path(explicit_path)
        if not overlay_path.is_file():
            raise FileNotFoundError(
                f"Configuration file selected by {CONFIG_FILE_ENV} not found: {overlay_path}"
            )
        merged = _deep_merge(merged, _read_yaml_mapping(overlay_path))
    else:
        local_path = default_path.parent / LOCAL_CONFIG_NAME
        if local_path.is_file():
            merged = _deep_merge(merged, _read_yaml_mapping(local_path))

    return _flatten_yaml_settings(merged)


def _resolve_default_config_path() -> Path:
    working_tree_path = _resolve_path(DEFAULT_CONFIG_PATH)
    if working_tree_path.exists():
        return working_tree_path
    repository_path = Path(__file__).resolve().parents[3] / DEFAULT_CONFIG_PATH
    return repository_path.resolve()


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate.resolve()


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file)
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    if not all(isinstance(key, str) for key in raw):
        raise ValueError(f"Configuration keys must be strings: {path}")
    return dict(raw)


def _deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _flatten_yaml_settings(config: Mapping[str, Any]) -> dict[str, Any]:
    unknown_sections = set(config) - set(_CONFIG_SCHEMA)
    if unknown_sections:
        names = ", ".join(sorted(unknown_sections))
        raise ValueError(f"Unknown configuration section(s): {names}")

    flattened: dict[str, Any] = {}
    for section, values in config.items():
        if not isinstance(values, Mapping):
            raise ValueError(f"Configuration section '{section}' must be a mapping")
        section_schema = _CONFIG_SCHEMA[section]
        unknown_fields = set(values) - set(section_schema)
        if unknown_fields:
            names = ", ".join(sorted(str(field) for field in unknown_fields))
            raise ValueError(f"Unknown field(s) in configuration section '{section}': {names}")

        for yaml_name, value in values.items():
            if not isinstance(yaml_name, str):
                raise ValueError(f"Configuration keys in section '{section}' must be strings")
            flattened[section_schema[yaml_name]] = value

    return flattened


@lru_cache
def get_settings() -> Settings:
    return Settings()
