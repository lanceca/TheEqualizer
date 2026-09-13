from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0003_email_security",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginAttemptThrottle",
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
                    "identifier_hash",
                    models.CharField(
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "failed_attempts",
                    models.PositiveSmallIntegerField(
                        default=0,
                    ),
                ),
                (
                    "locked_until",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                    ),
                ),
            ],
        ),
    ]
