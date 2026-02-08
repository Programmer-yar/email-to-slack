"""Slack API: upload files and post block messages."""

from .blocks import build_blocks_for_email
from .client import SlackClient

__all__ = ["SlackClient", "build_blocks_for_email"]
