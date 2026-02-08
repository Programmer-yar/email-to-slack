"""Configuration and constants derived from the n8n flow."""

import os
from pathlib import Path

from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Optional


def config_from_env() -> "Config":
    """Build Config from environment variables (and .env file if present)."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    allowed = os.environ.get(
        "IMAP_ALLOWED_FROM", "noreply@sandiego.gov,ahmadyar228@gmail.com"
    )
    return Config(
        imap=ImapConfig(
            host=os.environ.get("IMAP_HOST", ""),
            port=int(os.environ.get("IMAP_PORT", "993")),
            username=os.environ.get("IMAP_USERNAME", ""),
            password=os.environ.get("IMAP_PASSWORD", ""),
            allowed_from=[a.strip() for a in allowed.split(",") if a.strip()],
        ),
        slack=SlackConfig(
            token=os.environ.get("SLACK_BOT_TOKEN", ""),
        ),
    )


# Subject → output key (routing). Case-insensitive contains match.
SUBJECT_ROUTES = [
    ("recheck required", "recheck_required"),
    ("review is pending", "review_pending"),
    ("permit issu", "permit_issuance"),
    ("checklist requested", "checklist_required"),
    ("test flow", "test_flow"),
]

# Channel/user IDs from the n8n Slack nodes (replace via env in production).
CHANNEL_IDS = {
    "recheck_required": "C0ACMRV4JKY",   # recheck-required
    "review_pending": "C0ACHG9EFNF",     # pending-invoice-payment
    "permit_issuance": "C0ACHGN84BV",    # permit-issuance
    "checklist_required": "C0ACHGN84BV",  # permit-issuance
    "test_flow": None,  # sent to user, not channel
}

USER_IDS = {
    "test_flow": "U0ACD9N7ZTN",  # ahmadyar228
}


@dataclass
class ImapConfig:
    """IMAP connection and filter settings (from Yahoo Email Trigger node)."""
    host: str = ""
    port: int = 993
    use_ssl: bool = True
    username: str = ""
    password: str = ""
    # UNSEEN + allowed_from (e.g. noreply@sandiego.gov, ahmadyar228@gmail.com)
    allowed_from: list[str] = field(
        default_factory=lambda: ["ahmadyar228@gmail.com"] #"noreply@sandiego.gov",
    )


@dataclass
class SlackConfig:
    """Slack API settings."""
    token: str = ""
    # Override channel/user per route; else uses CHANNEL_IDS / USER_IDS.
    channel_ids: dict[str, Optional[str]] = field(default_factory=dict)
    user_ids: dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class Config:
    """Top-level configuration."""
    imap: ImapConfig = field(default_factory=ImapConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
