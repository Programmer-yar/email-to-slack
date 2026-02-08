"""Email fetching and parsing."""

from .fetcher import EmailFetcher
from .parser import parse_email_to_mrkdwn

__all__ = ["EmailFetcher", "parse_email_to_mrkdwn"]
