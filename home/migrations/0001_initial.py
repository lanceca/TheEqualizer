from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MobileAppSettings",
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
                    "current_version",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                (
                    "download_url",
                    models.URLField(
                        blank=True,
                        max_length=600,
                    ),
                ),
                (
                    "notice_enabled",
                    models.BooleanField(
                        default=False,
                    ),
                ),
                (
                    "notice_title",
                    models.CharField(
                        default=(
                            "A new version of The Equalizer app "
                            "is available."
                        ),
                        max_length=140,
                    ),
                ),
                (
                    "notice_message",
                    models.TextField(
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Mobile app settings",
                "verbose_name_plural": "Mobile app settings",
            },
        ),
    ]
