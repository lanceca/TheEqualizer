from django.db import models


class ArticleDailyAnalytics(models.Model):

    article = models.ForeignKey(
        "publications.Article",
        on_delete=models.CASCADE,
        related_name="daily_analytics",
    )

    date = models.DateField()

    views = models.PositiveBigIntegerField(
        default=0,
    )

    reactions = models.PositiveBigIntegerField(
        default=0,
    )

    shares = models.PositiveBigIntegerField(
        default=0,
    )

    downloads = models.PositiveBigIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "-date",
            "article_id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "article",
                    "date",
                ],
                name="unique_article_daily_analytics",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "date",
                ],
                name="analytics_date_idx",
            ),

            models.Index(
                fields=[
                    "article",
                    "date",
                ],
                name="analytics_article_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"{self.date}"
        )

class ArticlePdfDownloadTracker(models.Model):
    """
    Store one privacy-preserving PDF-download fingerprint per article.

    The fingerprint is a keyed digest generated from the request's client
    IP and browser/device headers. Raw identifying request values are not
    stored.
    """

    article = models.ForeignKey(
        "publications.Article",
        on_delete=models.CASCADE,
        related_name="pdf_download_trackers",
    )

    fingerprint_hash = models.CharField(
        max_length=64,
    )

    first_downloaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-first_downloaded_at",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "article",
                    "fingerprint_hash",
                ],
                name=(
                    "unique_article_pdf_download_fingerprint"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"{self.fingerprint_hash[:12]}"
        )

