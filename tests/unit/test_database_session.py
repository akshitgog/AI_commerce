from sqlalchemy import create_engine, text

from ai_commerce_gateway.infrastructure.database.session import (
    create_session_factory,
    session_scope,
)


def test_session_scope_commits() -> None:
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE sample (value INTEGER NOT NULL)"))
        factory = create_session_factory(engine)

        with session_scope(factory) as session:
            session.execute(text("INSERT INTO sample (value) VALUES (1)"))

        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM sample")).scalar_one() == 1
    finally:
        engine.dispose()


def test_session_scope_rolls_back() -> None:
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE sample (value INTEGER NOT NULL)"))
        factory = create_session_factory(engine)

        try:
            with session_scope(factory) as session:
                session.execute(text("INSERT INTO sample (value) VALUES (1)"))
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM sample")).scalar_one() == 0
    finally:
        engine.dispose()
