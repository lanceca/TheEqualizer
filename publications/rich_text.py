"""One allowlist for stored article HTML, reader previews and PDF output."""

import re
from html import escape, unescape
from html.parser import HTMLParser

import bleach


ALLOWED_TAGS = frozenset(
    {
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "strike",
        "p",
        "br",
        "ul",
        "ol",
        "li",
    }
)

HTML_TAG = re.compile(
    r"</?[a-zA-Z][^>]*>"
)


def _allowed_attribute(
    tag,
    name,
    value,
):
    """
    The editor uses one safe data attribute to distinguish a dash list
    from a normal unordered list. No arbitrary classes/styles survive.
    """

    return (
        tag == "ul"
        and name == "data-list-style"
        and value == "dash"
    )


def sanitize_article_content(value):
    value = (
        str(value or "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    # Preserve legacy plain text verbatim. Escape it only at render time.
    if not HTML_TAG.search(value):
        return value

    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=_allowed_attribute,
        protocols=[],
        strip=True,
    )

    # Retain an HTML marker when all original tags were stripped, so
    # entities are not double-escaped on the next save or decoded into
    # unsafe markup.
    return (
        cleaned
        if HTML_TAG.search(cleaned) or not cleaned
        else f"<p>{cleaned}</p>"
    )


def article_html(value):
    value = str(value or "")

    if not HTML_TAG.search(value):
        return (
            escape(value)
            .replace("\n", "<br>")
        )

    return (
        sanitize_article_content(value)
        .replace("\n", "<br>")
    )


class _PlainTextConverter(HTMLParser):
    """
    Turn sanitized article HTML into readable plain text.

    List markers are intentionally retained so version comparisons can
    distinguish bullets, numbered lists and dash lists.
    """

    def __init__(self):
        super().__init__(
            convert_charrefs=True,
        )

        self.parts = []
        self.list_stack = []

    def _newline(self):
        if (
            self.parts
            and not self.parts[-1].endswith("\n")
        ):
            self.parts.append("\n")

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(attrs)

        if tag in {"ul", "ol"}:
            self.list_stack.append(
                {
                    "type": tag,
                    "dash": (
                        tag == "ul"
                        and attrs.get(
                            "data-list-style"
                        ) == "dash"
                    ),
                    "index": 0,
                }
            )

        elif tag == "li":
            self._newline()

            if self.list_stack:
                current = self.list_stack[-1]
                current["index"] += 1

                if (
                    current["type"] == "ol"
                ):
                    marker = (
                        f'{current["index"]}. '
                    )
                elif current["dash"]:
                    marker = "— "
                else:
                    marker = "• "

                self.parts.append(marker)

        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(
        self,
        tag,
    ):
        if tag == "li":
            self._newline()

        elif tag == "p":
            self._newline()

        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()

            self._newline()

    def handle_data(
        self,
        data,
    ):
        self.parts.append(data)

    def text(self):
        return re.sub(
            r"\n{3,}",
            "\n\n",
            "".join(self.parts),
        ).rstrip("\n")


def article_plain_text(value):
    value = str(value or "")

    if not HTML_TAG.search(value):
        return value

    parser = _PlainTextConverter()

    parser.feed(
        article_html(value)
    )

    parser.close()

    return unescape(
        parser.text()
    )


class _PDFConverter(HTMLParser):
    """
    Translate sanitized HTML to ReportLab's small XML vocabulary.

    ReportLab Paragraph does not understand browser UL/OL elements, so
    lists are converted into line-broken markers while inline formatting
    remains intact.
    """

    aliases = {
        "strong": "b",
        "em": "i",
        "s": "strike",
    }

    def __init__(self):
        super().__init__(
            convert_charrefs=True,
        )

        self.parts = []
        self.list_stack = []

    def _line_break(self):
        if (
            self.parts
            and self.parts[-1] != "<br/>"
        ):
            self.parts.append("<br/>")

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(attrs)

        if tag == "br":
            self.parts.append("<br/>")
            return

        if tag in {"ul", "ol"}:
            self.list_stack.append(
                {
                    "type": tag,
                    "dash": (
                        tag == "ul"
                        and attrs.get(
                            "data-list-style"
                        ) == "dash"
                    ),
                    "index": 0,
                }
            )
            return

        if tag == "li":
            self._line_break()

            if self.list_stack:
                current = self.list_stack[-1]
                current["index"] += 1

                if (
                    current["type"] == "ol"
                ):
                    marker = (
                        f'{current["index"]}. '
                    )
                elif current["dash"]:
                    marker = "&#8212; "
                else:
                    marker = "&#8226; "

                self.parts.append(marker)

            return

        if (
            tag in ALLOWED_TAGS
            and tag
            not in {
                "p",
                "ul",
                "ol",
                "li",
            }
        ):
            converted = self.aliases.get(
                tag,
                tag,
            )

            self.parts.append(
                f"<{converted}>"
            )

    def handle_endtag(
        self,
        tag,
    ):
        if tag == "p":
            self._line_break()
            self.parts.append("<br/>")
            return

        if tag == "li":
            self._line_break()
            return

        if tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()

            self._line_break()
            return

        if (
            tag in ALLOWED_TAGS
            and tag != "br"
        ):
            converted = self.aliases.get(
                tag,
                tag,
            )

            self.parts.append(
                f"</{converted}>"
            )

    def handle_data(
        self,
        data,
    ):
        data = re.sub(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
            "",
            data,
        )

        self.parts.append(
            escape(data)
        )


def article_pdf_html(value):
    parser = _PDFConverter()

    parser.feed(
        article_html(value)
    )

    parser.close()

    return "".join(
        parser.parts
    )
