from django import template
from django.template.defaultfilters import truncatewords_html
from django.utils.safestring import mark_safe

from publications.rich_text import article_html, normalize_article_spacing

register = template.Library()


@register.filter
def article_display_text(value):
    """Render plain article metadata without leaking nested NBSP entities.

    This deliberately normalizes only the known whitespace entity forms handled
    by the central rich-text pipeline. The return value is *not* marked safe,
    so Django auto-escaping remains active for titles, captions, credits, tags,
    alt text, and other plain-text article fields.
    """
    return normalize_article_spacing(value)


@register.filter
def rich_article(value):
    # Only the allowlisted result may be marked safe, including old snapshots.
    return mark_safe(article_html(value))


@register.filter
def rich_article_preview(value, words=40):
    """Render a compact, sanitized rich-text article preview.

    The full article sanitizer remains authoritative. This preview helper
    additionally normalizes non-breaking-space entities so card excerpts do
    not leak literal strings such as ``&nbsp;`` when article HTML is used as
    the fallback summary.
    """

    try:
        limit = max(1, int(words))
    except (TypeError, ValueError):
        limit = 40

    # article_html() already applies the central whitespace normalizer
    # before escaping/sanitizing, so card previews share the exact same
    # entity handling as the reader article and staff reader preview.
    html = article_html(value)

    return mark_safe(
        truncatewords_html(
            html,
            limit,
        )
    )


@register.filter
def masked_email(value):
    local, separator, domain = str(value or "").partition("@")
    return f"{local[:1]}••••••••{separator}{domain}" if local else "Not provided"


@register.filter
def archive_wording(value):
    """Display historical notifications accurately without rewriting their records."""
    import re
    return re.sub(r"deletion(?= requests?\b)", "archive", str(value), flags=re.I)
