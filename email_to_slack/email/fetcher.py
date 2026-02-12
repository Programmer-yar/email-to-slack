"""Fetch emails via IMAP (equivalent to n8n Yahoo Email Trigger)."""

import imaplib
import logging
from email import policy
from email.parser import BytesParser

from ..config import ImapConfig

logger = logging.getLogger(__name__)


def _decode_header(value: str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _from_matches_allowed(from_header: str, allowed: list[str]) -> bool:
    from_lower = from_header.lower()
    for addr in allowed:
        if addr.lower() in from_lower:
            return True
    return False


class EmailFetcher:
    """Fetches unseen emails from IMAP and yields raw message data with attachments."""

    def __init__(self, config: ImapConfig) -> None:
        self.config = config

    def _connect(self) -> imaplib.IMAP4_SSL:
        logger.info(f"Connecting to IMAP server: {self.config.host}:{self.config.port}")
        try:
            conn = imaplib.IMAP4_SSL(self.config.host, self.config.port)
            conn.login(self.config.username, self.config.password)
            logger.info("Successfully connected to IMAP server")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            raise

    def fetch_unseen(self) -> list[dict]:
        """
        Fetch unseen emails from allowed senders.
        Returns list of dicts: uid, message_id, subject, date, from, html, attachments.
        """
        conn = self._connect()
        try:
            conn.select("INBOX")
            _, data = conn.search(None, "UNSEEN")
            uids = data[0].split()
            
            if not uids:
                logger.info("No unseen emails found")
                return []

            logger.info(f"Found {len(uids)} unseen email(s)")
            emails = []
            
            for uid in uids:
                uid_s = uid.decode() if isinstance(uid, bytes) else str(uid)
                # Peek at From header only; do not fetch or mark non-allowed emails.
                _, head_data = conn.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
                if not head_data or not head_data[0]:
                    continue
                raw_header = head_data[0][1]
                if raw_header is None:
                    continue
                from_header = _decode_header(
                    BytesParser(policy=policy.default).parsebytes(raw_header).get("From")
                )
                
                if not _from_matches_allowed(from_header, self.config.allowed_from):
                    logger.warning(f"Skipping email from non-allowed sender: {from_header}")
                    continue

                # Only allowed senders: fetch full message and mark as seen.
                _, msg_data = conn.fetch(uid, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = BytesParser(policy=policy.default).parsebytes(raw)

                subject = _decode_header(msg.get("Subject"))
                date = _decode_header(msg.get("Date"))
                message_id = _decode_header(msg.get("Message-ID")) or uid_s
                html = ""
                text_plain = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        filename = part.get_filename()
                        if filename:
                            continue  # attachment, handled below
                        if ctype == "text/html":
                            payload = part.get_payload(decode=True)
                            html = (payload or b"").decode(errors="replace")
                        elif ctype == "text/plain":
                            payload = part.get_payload(decode=True)
                            text_plain = (payload or b"").decode(errors="replace")
                else:
                    payload = msg.get_payload(decode=True)
                    decoded = (payload or b"").decode(errors="replace")
                    if msg.get_content_type() == "text/html":
                        html = decoded
                    else:
                        text_plain = decoded

                attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                "filename": filename,
                                "content": part.get_payload(decode=True) or b"",
                                "content_type": part.get_content_type(),
                            })

                emails.append({
                    "uid": uid_s,
                    "message_id": message_id,
                    "subject": subject,
                    "date": date,
                    "from": from_header,
                    "html": html or text_plain,
                    "attachments": attachments,
                })
                
                logger.info(f"Processed email: '{subject}' from {from_header}")
                conn.store(uid_s, "+FLAGS", "\\Seen")

            return emails
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise
        finally:
            try:
                conn.logout()
                logger.info("Disconnected from IMAP server")
            except Exception:
                pass
