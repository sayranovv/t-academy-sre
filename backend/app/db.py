from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


settings = get_settings()
engine = create_engine(
    settings.sqlalchemy_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": settings.db_connect_timeout,
        "options": (
            f"-c lock_timeout={settings.db_lock_timeout_ms} "
            f"-c statement_timeout={settings.db_statement_timeout_ms} -c timezone=UTC"
        ),
    },
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    # Services own transaction boundaries; cleanup must never commit implicitly.
    with SessionLocal() as session:
        yield session
