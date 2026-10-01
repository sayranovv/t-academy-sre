FROM ghcr.io/astral-sh/uv:0.9.7 AS uv
FROM python:3.14.5-slim-bookworm AS development
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
EXPOSE 8000
CMD ["python", "-m", "app.run"]

FROM python:3.14.5-slim-bookworm AS production
ARG APP_UID=10001
RUN adduser --disabled-password --gecos "" --home /nonexistent \
    --shell /usr/sbin/nologin --no-create-home --uid "${APP_UID}" appuser
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:$PATH"
COPY --from=development /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
USER appuser
EXPOSE 8000
CMD ["python", "-m", "app.run"]
