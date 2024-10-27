FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

# Create a non-root user named 'pythonuser' and an /app folder owned by that user
RUN useradd -m pythonuser \
    && mkdir -p /app \
    && chown pythonuser:pythonuser /app

# Set the working directory to /app
WORKDIR /app

# Copy the 'assets' folder contents to /app with the correct ownership
COPY --chown=pythonuser:pythonuser assets/ /app

# Set the user to 'pythonuser'
USER pythonuser

# Argument for the wheel file name
ARG WHEEL_FILE=my_wheel.whl

# Copy only the wheel file and install it
COPY dist/${WHEEL_FILE} /tmp/${WHEEL_FILE}
RUN pip install /tmp/${WHEEL_FILE} && rm /tmp/${WHEEL_FILE}

# Expose port 8080
EXPOSE 8080

# Define health check
HEALTHCHECK --interval=20s --timeout=20s --start-period=5s --retries=3 CMD ["curl", "--fail", "-so", "/dev/null", "http://127.0.0.1:8080/health"]

# Start the application
ENTRYPOINT [ "uvicorn", "tts_batch_api.main:app", "--host",  "0.0.0.0", "--port", "8080" ]
