"""Sanitize every saved article body, including admin edits and snapshots."""
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Article, ArticleVersion, Submission
from .rich_text import sanitize_article_content


@receiver(pre_save, sender=Article)
@receiver(pre_save, sender=ArticleVersion)
@receiver(pre_save, sender=Submission)
def sanitize_saved_article(sender, instance, **kwargs):
    field = "snapshot_content" if sender is Submission else "content"
    setattr(instance, field, sanitize_article_content(getattr(instance, field)))
