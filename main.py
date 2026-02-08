"""Entrypoint: run email fetch -> parse -> Slack when IMAP_HOST and SLACK_BOT_TOKEN are set."""

import os
import sys


def main() -> None:
    if not os.environ.get("IMAP_HOST") or not os.environ.get("SLACK_BOT_TOKEN"):
        print(
            "Set IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD, SLACK_BOT_TOKEN "
            "(and optionally STATE_FILE)",
            file=sys.stderr,
        )
        sys.exit(1)

    from email_to_slack.email import EmailFetcher, parse_email_to_mrkdwn
    from email_to_slack.config import (
        SUBJECT_ROUTES,
        CHANNEL_IDS,
        USER_IDS,
        config_from_env,
    )
    from email_to_slack.slack import SlackClient, build_blocks_for_email

    config = config_from_env()
    fetcher = EmailFetcher(config.imap)
    slack = SlackClient(config.slack.token)

    emails = fetcher.fetch_unseen()
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
        ch_ids = config.slack.channel_ids or CHANNEL_IDS
        channel_id = ch_ids.get(route_key) if route_key else None
        u_ids = config.slack.user_ids or USER_IDS
        user_id = u_ids.get(route_key) if route_key else None
        file_links = []
        for att in em.get("attachments") or []:
            up = slack.upload_file(
                content=att["content"],
                filename=att.get("filename", "attachment"),
                channel_id=channel_id,
            )
            if up and up.get("permalink"):
                file_links.append({"name": up["name"], "url": up["permalink"]})
        blocks = build_blocks_for_email(
            subject=parsed.subject,
            date=parsed.date,
            text_content=parsed.text_content,
            file_links=file_links,
        )
        slack.post_blocks(
            blocks=blocks,
            channel_id=channel_id,
            user_id=user_id,
            text=f"City of San Diego: {parsed.subject}",
        )


if __name__ == "__main__":
    main()
