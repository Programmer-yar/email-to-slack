"""Convert email HTML to Slack mrkdwn (equivalent to n8n 'html to text' node)."""

from dataclasses import dataclass


@dataclass
class ParsedEmail:
    """Parsed email data ready for Slack blocks."""
    text_content: str
    subject: str
    date: str
    from_addr: str
    email_id: str


def _extract_href(tag: str) -> str | None:
    """Extract href value from an anchor tag string (no regex)."""
    tag_lower = tag.lower()
    href_pos = tag_lower.find("href=")
    if href_pos == -1:
        return None

    start = href_pos + 5
    if start >= len(tag):
        return None

    quote_char = tag[start]
    if quote_char not in ("\"", "'"):
        end = start
        while end < len(tag) and tag[end] not in (" ", ">", "\t"):
            end += 1
        return tag[start:end]

    end = tag.find(quote_char, start + 1)
    if end == -1:
        return None
    return tag[start + 1 : end]


def _convert_links_to_slack(html: str) -> str:
    """Convert <a href='URL'>text</a> to Slack mrkdwn format <URL|text>."""
    result = ""
    i = 0

    while i < len(html):
        if html[i] == "<" and i + 2 < len(html) and html[i + 1 : i + 3].lower() in (
            "a ",
            "a\t",
            "a>",
        ):
            tag_end = html.find(">", i)
            if tag_end == -1:
                result += html[i]
                i += 1
                continue

            opening_tag = html[i : tag_end + 1]
            href = _extract_href(opening_tag)

            close_tag = html.lower().find("</a>", tag_end)
            if close_tag == -1:
                result += html[i]
                i += 1
                continue

            link_text = html[tag_end + 1 : close_tag]

            clean_text = ""
            in_tag = False
            for c in link_text:
                if c == "<":
                    in_tag = True
                elif c == ">":
                    in_tag = False
                elif not in_tag:
                    clean_text += c
            clean_text = clean_text.strip()

            if href:
                if clean_text:
                    result += "<" + href + "|" + clean_text + ">"
                else:
                    result += "<" + href + ">"
            else:
                result += clean_text

            i = close_tag + 4
        else:
            result += html[i]
            i += 1

    return result


def _html_to_slack_mrkdwn(html: str) -> str:
    """Convert HTML to Slack mrkdwn format."""
    html = _convert_links_to_slack(html)

    html = html.replace("<b>", "*").replace("</b>", "*")
    html = html.replace("<B>", "*").replace("</B>", "*")
    html = html.replace("<strong>", "*").replace("</strong>", "*")
    html = html.replace("<STRONG>", "*").replace("</STRONG>", "*")
    html = html.replace("<i>", "_").replace("</i>", "_")
    html = html.replace("<I>", "_").replace("</I>", "_")
    html = html.replace("<em>", "_").replace("</em>", "_")
    html = html.replace("<EM>", "_").replace("</EM>", "_")

    html = html.replace("<br>", "\n").replace("<BR>", "\n")
    html = html.replace("<br/>", "\n").replace("<BR/>", "\n")
    html = html.replace("<br />", "\n").replace("<BR />", "\n")
    html = html.replace("<p>", "\n").replace("<P>", "\n")
    html = html.replace("</p>", "\n").replace("</P>", "\n")
    html = html.replace("<div>", "\n").replace("<DIV>", "\n")
    html = html.replace("</div>", "").replace("</DIV>", "")

    result = ""
    i = 0
    while i < len(html):
        if html[i] == "<":
            rest = (html[i + 1 : i + 10].lower()) if i + 1 < len(html) else ""
            if rest.startswith("http") or rest.startswith("mailto") or rest.startswith("tel:"):
                end = html.find(">", i)
                if end != -1:
                    result += html[i : end + 1]
                    i = end + 1
                    continue
            end = html.find(">", i)
            if end != -1:
                i = end + 1
            else:
                i += 1
        else:
            result += html[i]
            i += 1

    text = result
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&rsquo;", "'")
    text = text.replace("&lsquo;", "'")
    text = text.replace("&rdquo;", '"')
    text = text.replace("&ldquo;", '"')
    text = text.replace("&ndash;", "-")
    text = text.replace("&mdash;", "-")

    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        for marker in ["_", "*"]:
            count = line.count(marker)
            if count % 2 == 1:
                line = line.replace(marker, "")
        while "  " in line:
            line = line.replace("  ", " ")
        cleaned_lines.append(line.strip())

    text = "\n".join(cleaned_lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    while text.startswith("\n"):
        text = text[1:]
    while text.endswith("\n"):
        text = text[:-1]

    return text


def parse_email_to_mrkdwn(
    *,
    html: str,
    subject: str,
    date: str,
    from_addr: str,
    email_id: str,
) -> ParsedEmail:
    """Parse one email into Slack-ready text and metadata (n8n 'html to text' step)."""
    content = _html_to_slack_mrkdwn(html).strip()
    return ParsedEmail(
        text_content=content,
        subject=subject,
        date=date,
        from_addr=from_addr,
        email_id=email_id,
    )
