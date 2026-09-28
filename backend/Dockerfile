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
