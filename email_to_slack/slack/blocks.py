"""Build Slack Block Kit from parsed email (equivalent to n8n 'dynamic slack blocks' node)."""

from typing import Any


def build_blocks_for_email(
    *,
    subject: str,
    date: str,
    text_content: str,
    file_links: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """
    Build Slack blocks for one email: header, date, body, then attachment links.
    file_links: list of {"name": "...", "url": "..."} from upload step.
    """
    blocks: list[dict[str, Any]] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{subject}*"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"_Date: {date}_"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": text_content}},
    ]
    if file_links:
        blocks.append({"type": "divider"})
        for file in file_links:
            name = file.get("name", "file")
            url = file.get("url", "")
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"📎 *Attachment:* <{url}|{name}>"},
            })
    return blocks
