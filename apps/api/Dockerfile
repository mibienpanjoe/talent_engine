FROM python:3.13-slim@sha256:bb2988715db2cf7ace7b53f38f3cffbef7c7046a656bee66245eb0ed386e2e81
RUN pip install --no-cache-dir --progress-bar off --timeout 30 --retries 2 uv==0.12.15
RUN useradd --create-home --uid 10001 talent
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY apps/api/src ./src
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./
RUN uv sync --locked --no-dev && chown -R talent:talent /app
USER talent
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
CMD ["uvicorn", "talent_engine.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
