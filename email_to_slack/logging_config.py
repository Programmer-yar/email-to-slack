"""Centralized logging configuration for email-to-slack application."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Suppress verbose third-party library logs
    logging.getLogger("slack_sdk").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
