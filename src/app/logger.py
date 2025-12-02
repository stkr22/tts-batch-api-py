"""Centralized logging configuration for TTS Batch API.

This module configures application-wide logging with environment-based
log levels and structured formatting for container environments.
"""

import logging
import os
import sys

# AIDEV-NOTE: logging-config; centralized logging setup for container environments
# Configure logging with environment-based level
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,  # Container-friendly: logs to stdout for aggregation
)

# Main application logger
logger = logging.getLogger("TTS Batch API")
