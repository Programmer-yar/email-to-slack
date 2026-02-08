"""Entrypoint: run email fetch -> parse -> Slack when IMAP_HOST and SLACK_BOT_TOKEN are set."""

import os
import sys


def main() -> None:
    # TODO: check for environment variables
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
    # emails = [{'uid': '10000', 'message_id': '<CAO5dYahNK20z+4dX3snGdEvZ6u4HTTV5n5SA8BjVrjHyRtovLQ@mail.gmail.com>', 'subject': 'test flow', 'date': 'Sun, 08 Feb 2026 14:33:39 +0500', 'from': 'Ahmad Yar <ahmadyar228@gmail.com>', 'html': '<div dir="ltr"><i>Hi,<br>This is an email to <b>test</b> the flow</i></div>\r\n', 'attachments': []}]
    print(f"Emails: {emails}")
    for em in emails:
        print(f"Email: {em}")
        parsed = parse_email_to_mrkdwn(
            html=em["html"],
            subject=em["subject"],
            date=em["date"],
            from_addr=em["from"],
            email_id=em["message_id"],
        )
        print(f"Parsed: {parsed}")
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
        print(f"Blocks: {blocks}")
        slack.post_blocks(
            blocks=blocks,
            channel_id=channel_id,
            user_id=user_id,
            text=f"City of San Diego: {parsed.subject}",
        )


if __name__ == "__main__":
    main()
