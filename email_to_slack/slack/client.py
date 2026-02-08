"""Slack API client: upload file and post message with blocks."""

from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    """Upload files to Slack and post block messages to channels or users."""

    def __init__(self, token: str) -> None:
        self._client = WebClient(token=token)

    def upload_file(
        self,
        *,
        content: bytes,
        filename: str,
        channels: list[str] | None = None,
        channel_id: str | None = None,
        initial_comment: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Upload a file. Returns dict with 'permalink' and 'name' on success, None on failure.
        For Block Kit flow we need the file permalink; channel is optional for upload.
        """
        try:
            if channel_id:
                channels = [channel_id]
            result = self._client.files_upload_v2(
                file=content,
                filename=filename,
                channel=channels[0] if channels else None,
                initial_comment=initial_comment,
            )
            # files_upload_v2 returns different shape; we need file permalink
            if not result.get("ok"):
                return None
            file_info = result.get("file") or {}
            return {
                "permalink": file_info.get("permalink") or file_info.get("url_private"),
                "name": filename,
                "title": file_info.get("title") or filename,
            }
        except SlackApiError:
            return None

    def post_blocks(
        self,
        *,
        blocks: list[dict[str, Any]],
        channel_id: str | None = None,
        user_id: str | None = None,
        text: str = "City of San Diego Email",
    ) -> bool:
        """Post a message with Block Kit blocks. Both channel_id and user_id are used as channel target."""
        try:
            channel = channel_id or user_id
            if not channel:
                return False
            self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
            )
            return True
        except SlackApiError:
            return False
