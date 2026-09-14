from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            "analytics",
            "0002_articledailyanalytics_downloads",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticlePdfDownloadTracker",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "fingerprint_hash",
                    models.CharField(
                        max_length=64,
                    ),
                ),
                (
                    "first_downloaded_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name=(
                            "pdf_download_trackers"
                        ),
                        to="publications.article",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "-first_downloaded_at",
                    "-id",
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="articlepdfdownloadtracker",
            constraint=models.UniqueConstraint(
                fields=(
                    "article",
                    "fingerprint_hash",
                ),
                name=(
                    "unique_article_pdf_download_fingerprint"
                ),
            ),
        ),
    ]
