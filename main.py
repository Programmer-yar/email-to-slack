"""Entrypoint: run email fetch -> parse -> Slack when IMAP_HOST and SLACK_BOT_TOKEN are set."""

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    from email_to_slack.logging_config import setup_logging
    from email_to_slack.email import EmailFetcher, parse_email_to_mrkdwn
    from email_to_slack.config import (
        SUBJECT_ROUTES,
        CHANNEL_IDS,
        USER_IDS,
        config_from_env,
    )
    from email_to_slack.slack import SlackClient, build_blocks_for_email

    setup_logging()
    
    config = config_from_env()
    fetcher = EmailFetcher(config.imap)
    slack = SlackClient(config.slack.token)

    emails = fetcher.fetch_unseen()
    logger.info(f"Fetched {len(emails)} unseen emails")
    
    if not emails:
        logger.info("No unseen emails to process")
        return
    
    for em in emails:
        parsed = parse_email_to_mrkdwn(
            html=em["html"],
            subject=em["subject"],
            date=em["date"],
            from_addr=em["from"],
            email_id=em["message_id"],
        )
        
        route_key = None
        for phrase, key in SUBJECT_ROUTES:
            if phrase.lower() in (em["subject"] or "").lower():
                route_key = key
                break
        
        if not route_key:
            logger.warning(f"No route matched for email subject: {em['subject']}")
        
        ch_ids = config.slack.channel_ids or CHANNEL_IDS
        channel_id = ch_ids.get(route_key) if route_key else None
        u_ids = config.slack.user_ids or USER_IDS
        user_id = u_ids.get(route_key) if route_key else None
        
        if not channel_id and not user_id:
            logger.error(f"No channel or user ID found for route: {route_key}")
            continue
        
        # Check if there are attachments
        attachments = em.get("attachments") or []
        has_attachments = len(attachments) > 0
        
        # Build blocks with attachments section if needed
        blocks = build_blocks_for_email(
            subject=parsed.subject,
            date=parsed.date,
            text_content=parsed.text_content,
            has_attachments=has_attachments,
        )
        
        # Post the message first
        slack.post_blocks(
            blocks=blocks,
            channel_id=channel_id,
            user_id=user_id,
            text=f"City of San Diego: {parsed.subject}",
        )
        
        # Then upload attachments (they will appear as separate messages after)
        if has_attachments:
            logger.info(f"Uploading {len(attachments)} attachment(s) for email: {em['subject']}")
            for att in attachments:
                slack.upload_file(
                    content=att["content"],
                    filename=att.get("filename", "attachment"),
                    channel_id=channel_id,
                    user_id=user_id,
                )


if __name__ == "__main__":
    main()
