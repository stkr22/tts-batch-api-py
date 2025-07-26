# Build stage: Python 3.12.8-bookworm  
FROM docker.io/library/python:3.12.8-bookworm@sha256:68ca65265c466f4b64f8ddab669e13bcba8d4ba77ec4c26658d36f2b9d1b1cad as build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.21@sha256:a8d9b557b6cd6ede1842b0e03cd7ac26870e2c6b4eea4e10dab67cbd3145f8d9 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only
RUN --mount=type=cache,target=/root/.cache \
    uv venv && \
    uv sync --frozen --no-dev

# Runtime stage: Python 3.12.8-slim-bookworm
FROM docker.io/library/python:3.12.8-slim-bookworm@sha256:10f3aaab98db50cba827d3b33a91f39dc9ec2d02ca9b85cbc5008220d07b17f3

ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app

# Copy virtual environment from build stage
COPY --from=build-python /app/.venv /app/.venv

# Copy application source code and assets
COPY app/ /app/app/
COPY assets/ /app/assets/

ENV PATH="/app/.venv/bin:$PATH"

# Set the user to 'appuser'
USER appuser

# Expose the application port
EXPOSE 8080

# Start the application as the non-root user
CMD ["fastapi", "run", "app/main.py:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "8080"]
