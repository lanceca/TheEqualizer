from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0026_alter_peopleprofile_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchiveRecommendation",
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
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="archive_recommendations",
                        to="publications.article",
                    ),
                ),
                (
                    "recommended_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="archive_recommendations_sent",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="archive_recommendations_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
