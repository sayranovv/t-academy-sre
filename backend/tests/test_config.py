from pydantic import SecretStr

from app.config import Settings


def test_database_url_does_not_require_separate_password():
    settings = Settings(
        database_url=SecretStr("postgresql://operator:secret@postgres:5432/inventory"),
        db_password=SecretStr(""),
    )
    assert settings.sqlalchemy_url.drivername == "postgresql+psycopg"
    assert settings.sqlalchemy_url.database == "inventory"


def test_separate_credentials_are_not_interpolated_into_url():
    settings = Settings(database_url=None, db_password=SecretStr("pass@word:/?#"))
    assert settings.sqlalchemy_url.password == "pass@word:/?#"
