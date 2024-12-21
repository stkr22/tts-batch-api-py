FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin -M appuser \
    && mkdir -p /app /app/config \
    && chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy and install the wheel file
ARG WHEEL_FILE=my_wheel.whl
COPY dist/${WHEEL_FILE} /tmp/${WHEEL_FILE}

# Install dependencies and clean up in one layer
RUN pip install --no-cache-dir /tmp/${WHEEL_FILE} \
    && rm -rf /tmp/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /root/.cache/*

# Copy the 'assets' folder contents to /app with the correct ownership
COPY --chown=appuser:appuser assets/ /app

# Set the user to 'appuser'
USER appuser

# Expose port 8080
EXPOSE 8080

# Define health check
HEALTHCHECK --interval=20s --timeout=20s --start-period=5s --retries=3 CMD ["curl", "--fail", "-so", "/dev/null", "http://127.0.0.1:8080/health"]

# Start the application
ENTRYPOINT [ "uvicorn", "tts_batch_api.main:app", "--host",  "0.0.0.0", "--port", "8080" ]
