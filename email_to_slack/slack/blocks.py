"""Build Slack Block Kit from parsed email (equivalent to n8n 'dynamic slack
blocks' node)."""

from typing import Any


def build_blocks_for_email(
    *,
    subject: str,
    date: str,
    text_content: str,
    has_attachments: bool = False,
) -> list[dict[str, Any]]:
    """
    Build Slack blocks for one email: header, date, body, and optional
    attachments section.
    has_attachments: if True, adds an "Attachments" section at the end.
    """
    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{subject}*"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_Date: {date}_"},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": text_content}},
    ]
    if has_attachments:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📎 Attachments*"},
        })
    return blocks
