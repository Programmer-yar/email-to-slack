"""Slack API client: upload file and post message with blocks."""

import logging
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


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
        
        if not channel:
            logger.error("No channel or user ID provided for file upload")
            return None
        
        # Build kwargs - only include channel if it's valid
        upload_kwargs = {
            "file": content,
            "filename": filename,
        }
        
        if channel:
            upload_kwargs["channel"] = channel
        
        if initial_comment:
            upload_kwargs["initial_comment"] = initial_comment
        
        try:
            result = self._client.files_upload_v2(**upload_kwargs)
            
            if not result.get("ok"):
                logger.error(f"Failed to upload file '{filename}': {result.get('error', 'Unknown error')}")
                return None
            
            logger.info(f"Successfully uploaded file: {filename}")
            
            file_info = result.get("file") or {}
            return {
                "permalink": file_info.get("permalink") or file_info.get("url_private"),
                "name": filename,
                "title": file_info.get("title") or filename,
            }
        except SlackApiError as e:
            logger.error(f"Slack API error uploading file '{filename}': {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading file '{filename}': {e}")
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
        channel = channel_id or user_id
        if not channel:
            logger.error("No channel or user ID provided for posting message")
            return False
        
        try:
            self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
            )
            logger.info(f"Successfully posted message to channel/user: {channel}")
            return True
        except SlackApiError as e:
            logger.error(f"Slack API error posting message: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error posting message: {e}")
            return False
