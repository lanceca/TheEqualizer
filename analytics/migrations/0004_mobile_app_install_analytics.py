from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "analytics",
            "0003_articlepdfdownloadtracker",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="MobileAppInstallThrottle",
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
                        unique=True,
                    ),
                ),
                (
                    "last_counted_at",
                    models.DateTimeField(),
                ),
            ],
            options={
                "ordering": [
                    "-last_counted_at",
                    "-id",
                ],
            },
        ),
        migrations.CreateModel(
            name="MobileAppInstallEvent",
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
                    "app_version",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                (
                    "recorded_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "-recorded_at",
                    "-id",
                ],
                "indexes": [
                    models.Index(
                        fields=[
                            "recorded_at",
                        ],
                        name=(
                            "mobile_install_date_idx"
                        ),
                    ),
                    models.Index(
                        fields=[
                            "app_version",
                        ],
                        name=(
                            "mobile_install_ver_idx"
                        ),
                    ),
                ],
            },
        ),
    ]
