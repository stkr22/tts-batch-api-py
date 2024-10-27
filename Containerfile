FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

ARG WHEEL_FILE=my_wheel.wh

# Copy only the wheel file
COPY dist/${WHEEL_FILE} /tmp/${WHEEL_FILE}

# Install the package
RUN pip install /tmp/${WHEEL_FILE} && \
    rm /tmp/${WHEEL_FILE}

EXPOSE 8080

HEALTHCHECK --interval=20s --timeout=20s --start-period=5s --retries=3 CMD ["curl", "--fail", "-so", "/dev/null", "http://127.0.0.1:8080/health"]

ENTRYPOINT [ "uvicorn", "tts_batch_api.main:app", "--host",  "0.0.0.0", "--port", "8080" ]
