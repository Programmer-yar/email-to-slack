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
        user_id: str | None = None,
        initial_comment: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Upload a file using files_upload_v2 from Slack SDK.
        Both channel_id and user_id are used as channel target (channel_id takes precedence).
        Returns dict with 'permalink' and 'name' on success, None on failure.
        """
        # Determine which channel to use (channel_id takes precedence)
        channel = channel_id or user_id
        
        print(f"Uploading file: {filename}")
        print(f"  channel_id: {channel_id}")
        print(f"  user_id: {user_id}")
        print(f"  final channel: {channel}")
        print(f"  content length: {len(content)} bytes")
        
        # Build kwargs - only include channel if it's valid
        upload_kwargs = {
            "file": content,
            "filename": filename,
        }
        
        if channel:
            upload_kwargs["channel"] = channel
        
        if initial_comment:
            upload_kwargs["initial_comment"] = initial_comment
        
        result = self._client.files_upload_v2(**upload_kwargs)
        
        print(f"Upload result: {result}")
        
        if not result.get("ok"):
            return None
        
        file_info = result.get("file") or {}
        return {
            "permalink": file_info.get("permalink") or file_info.get("url_private"),
            "name": filename,
            "title": file_info.get("title") or filename,
        }

    def post_blocks(
        self,
        *,
        blocks: list[dict[str, Any]],
        channel_id: str | None = None,
        user_id: str | None = None,
        text: str = "City of San Diego Email",
    ) -> bool:
        """Post a message with Block Kit blocks. Both channel_id and user_id are used as channel target."""
        channel = channel_id or user_id
        if not channel:
            return False
        self._client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
        )
        return True
