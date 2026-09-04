import re
from pathlib import Path

import pytest
from pydantic import ValidationError

import ai_commerce_gateway.core.config as config_module
from ai_commerce_gateway.core.config import CONFIG_FILE_ENV, Settings


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(CONFIG_FILE_ENV, raising=False)
    _write(
        tmp_path / "config/default.yaml",
        """
app:
  environment: test
database:
  url: postgresql+psycopg://default/database
  pool_size: 5
llm:
  model: default-model
""",
    )


def test_default_and_local_yaml_deep_merge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate(monkeypatch, tmp_path)
    _write(
        tmp_path / "config/local.yaml",
        "llm:\n  model: local-model\n  api_key: local-secret\ndatabase:\n  pool_size: 12\n",
    )

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://default/database"
    assert settings.db_pool_size == 12
    assert settings.llm_model == "local-model"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "local-secret"


def test_explicit_deployment_yaml_works_without_repository_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", tmp_path / "absent.yaml")
    selected = _write(
        tmp_path / "deploy.yaml",
        """
app:
  environment: production
database:
  url: sqlite:///deploy.db
llm:
  model: deploy-model
""",
    )
    monkeypatch.setenv(CONFIG_FILE_ENV, str(selected))

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.database_url == "sqlite:///deploy.db"
    assert settings.llm_model == "deploy-model"


def test_environment_and_init_override_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///environment.db")
    monkeypatch.setenv("LLM_MODEL", "environment-model")

    settings = Settings(llm_model="init-model", _env_file=None)

    assert settings.database_url == "sqlite:///environment.db"
    assert settings.llm_model == "init-model"


def test_secrets_are_redacted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    settings = Settings(
        llm_api_key="llm-secret",
        razorpay_key_secret="api-secret",
        razorpay_webhook_secret="webhook-secret",
        merchant_mcp_publication_secret="publication-secret",
        _env_file=None,
    )
    rendered = repr(settings)
    for secret in ("llm-secret", "api-secret", "webhook-secret", "publication-secret"):
        assert secret not in rendered


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("unknown:\n  value: true\n", "Unknown configuration section(s): unknown"),
        ("llm:\n  typo: model\n", "Unknown field(s) in configuration section 'llm'"),
        ("llm: model\n", "Configuration section 'llm' must be a mapping"),
        ("- llm\n", "Configuration root must be a mapping"),
    ],
)
def test_invalid_yaml_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    _isolate(monkeypatch, tmp_path)
    selected = _write(tmp_path / "invalid.yaml", content)
    monkeypatch.setenv(CONFIG_FILE_ENV, str(selected))
    with pytest.raises(ValueError, match=re.escape(message)):
        Settings(_env_file=None)


def test_invalid_typed_value_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    _write(tmp_path / "config/local.yaml", "llm:\n  temperature: 3\n")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_missing_selected_file_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv(CONFIG_FILE_ENV, str(tmp_path / "missing.yaml"))
    with pytest.raises(FileNotFoundError, match=CONFIG_FILE_ENV):
        Settings(_env_file=None)
