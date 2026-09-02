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