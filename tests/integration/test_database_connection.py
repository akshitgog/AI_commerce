import pytest
from sqlalchemy import create_engine, text

from ai_commerce_gateway.core.config import get_settings


@pytest.mark.integration
def test_postgresql_connection_when_configured() -> None:
    database_url = get_settings().test_database_url
    if not database_url:
        pytest.skip("database.test_url is not configured")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
