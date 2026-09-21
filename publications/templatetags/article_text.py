from django import template
from django.utils.safestring import mark_safe

from publications.rich_text import article_html

register = template.Library()


@register.filter
def rich_article(value):
    # Only the allowlisted result may be marked safe, including old snapshots.
    return mark_safe(article_html(value))


@register.filter
def masked_email(value):
    local, separator, domain = str(value or "").partition("@")
    return f"{local[:1]}••••••••{separator}{domain}" if local else "Not provided"


@register.filter
def archive_wording(value):
    """Display historical notifications accurately without rewriting their records."""
    import re
    return re.sub(r"deletion(?= requests?\b)", "archive", str(value), flags=re.I)
