# Build stage: Python 3.11.11-bookworm
FROM docker.io/library/python:3.11.11-bookworm@sha256:08471c63c5fdf2644adc142a7fa8d0290eb405cda14c473fbe5b4cd0933af601 as build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.5.20 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy the application into the container.
COPY pyproject.toml README.md uv.lock /app/
COPY assets /app/assets
COPY app /app/app

RUN --mount=type=cache,target=/root/.cache \
    cd /app && \
    uv sync \
        --frozen \
        --no-group dev \
        --group prod

# runtime stage: Python 3.11.11-slim-bookworm
FROM docker.io/library/python:3.11.11-slim-bookworm@sha256:08471c63c5fdf2644adc142a7fa8d0290eb405cda14c473fbe5b4cd0933af601

ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app
COPY --from=build-python /app /app

ENV PATH="/app/.venv/bin:$PATH"

# Set the user to 'appuser'
USER appuser

# Expose the application port
EXPOSE 8080

# Start the application as the non-root user
CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--host", "0.0.0.0", "--port", "8080"]
