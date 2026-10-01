from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: SecretStr | None = None
    db_host: str = "db"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "equipment"
    db_user: str = "equipment"
    db_password: SecretStr = SecretStr("")
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=0, ge=0)
    db_pool_timeout: int = Field(default=5, ge=1)
    db_connect_timeout: int = Field(default=3, ge=1)
    db_lock_timeout_ms: int = Field(default=2000, ge=1)
    db_statement_timeout_ms: int = Field(default=5000, ge=1)
    readiness_timeout: float = Field(default=2, gt=0)
    shutdown_timeout: int = Field(default=20, ge=1)
    max_request_body_bytes: int = Field(default=32768, ge=1024)
    log_level: str = "info"
    reload: bool = False

    @property
    def sqlalchemy_url(self) -> URL:
        if self.database_url:
            url = make_url(self.database_url.get_secret_value())
            if url.get_backend_name() != "postgresql":
                raise ValueError("Only PostgreSQL is supported")
            return url.set(drivername="postgresql+psycopg")
        if not self.db_password.get_secret_value():
            raise ValueError("Set DATABASE_URL or DB_PASSWORD")
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
