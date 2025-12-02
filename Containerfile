# Build stage: Python 3.12.8-bookworm
FROM docker.io/library/python:3.13.9-trixie@sha256:5af92a47f819b7a6ec0bb3806862fe2cef7ea345e463be1a56c2830152cbac65 AS build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.9.14@sha256:fef8e5fb8809f4b57069e919ffcd1529c92b432a2c8d8ad1768087b0b018d840 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (excluding the current package)
RUN --mount=type=cache,target=/root/.cache \
    uv venv && \
    uv sync --frozen --no-dev --no-install-project

# Runtime stage: Python 3.12.8-slim-bookworm
FROM docker.io/library/python:3.13.9-slim-trixie@sha256:326df678c20c78d465db501563f3492d17c42a4afe33a1f2bf5406a1d56b0e86

ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app

# Copy virtual environment from build stage
COPY --from=build-python /app/.venv /app/.venv

# Copy application source code and scripts
COPY src/app /app/app
COPY scripts/ /app/scripts/

ENV PATH="/app/.venv/bin:$PATH"

# Download voice models using configuration
RUN python /app/scripts/download_models.py

# Set the user to 'appuser'
USER appuser

# Expose the application port
EXPOSE 8080

# Start the application as the non-root user
CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--host", "0.0.0.0", "--port", "8080"]
