FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.5.9 /uv /uvx /bin/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin -M appuser

# Copy the application into the container.
COPY pyproject.toml README.md uv.lock /app
COPY app /app/app
COPY assets /app/assets
RUN uv sync --frozen --no-cache

# Set the user to 'appuser'
USER appuser

# Expose port 8080
EXPOSE 8080

# Define health check
HEALTHCHECK --interval=20s --timeout=20s --start-period=5s --retries=3 CMD ["curl", "--fail", "-so", "/dev/null", "http://127.0.0.1:8080/health"]

# Start the application as the non-root user
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--proxy-headers", "--host", "0.0.0.0", "--port", "8080"]
