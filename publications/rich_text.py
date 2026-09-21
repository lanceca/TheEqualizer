"""One allowlist for stored article HTML, reader previews and PDF output."""
import re
from html import escape, unescape
from html.parser import HTMLParser

import bleach

ALLOWED_TAGS = frozenset({"strong", "b", "em", "i", "u", "s", "strike", "p", "br"})
HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def sanitize_article_content(value):
    value = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    # Preserve legacy plain text verbatim. Escape it only at rendering time.
    if not HTML_TAG.search(value):
        return value
    cleaned = bleach.clean(value, tags=ALLOWED_TAGS, attributes={}, protocols=[], strip=True)
    # Retain an HTML marker when all original tags were stripped, so entities
    # are not double-escaped on the next save or decoded into unsafe markup.
    return cleaned if HTML_TAG.search(cleaned) or not cleaned else f"<p>{cleaned}</p>"


def article_html(value):
    value = str(value or "")
    if not HTML_TAG.search(value):
        return escape(value).replace("\n", "<br>")
    return sanitize_article_content(value).replace("\n", "<br>")


def article_plain_text(value):
    value = str(value or "")
    if not HTML_TAG.search(value):
        return value
    value = re.sub(r"<br\s*/?>|</p>", "\n", article_html(value), flags=re.I)
    value = re.sub(r"<p>", "", value, flags=re.I)
    return unescape(bleach.clean(value, tags=[], attributes={}, strip=True))


class _PDFConverter(HTMLParser):
    """Translate sanitized HTML to ReportLab's small XML vocabulary."""
    aliases = {"strong": "b", "em": "i", "s": "strike"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("<br/>")
        elif tag in ALLOWED_TAGS and tag != "p":
            self.parts.append(f"<{self.aliases.get(tag, tag)}>")

    def handle_endtag(self, tag):
        if tag == "p":
            self.parts.append("<br/><br/>")
        elif tag in ALLOWED_TAGS and tag != "br":
            self.parts.append(f"</{self.aliases.get(tag, tag)}>")

    def handle_data(self, data):
        data = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", data)
        self.parts.append(escape(data))


def article_pdf_html(value):
    parser = _PDFConverter()
    parser.feed(article_html(value))
    parser.close()
    return "".join(parser.parts)
