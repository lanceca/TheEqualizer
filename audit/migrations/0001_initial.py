from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="ActionLog",
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
                    "actor_username_snapshot",
                    models.CharField(
                        blank=True,
                        max_length=150,
                    ),
                ),
                (
                    "actor_role_snapshot",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        db_index=True,
                        max_length=80,
                    ),
                ),
                (
                    "module",
                    models.CharField(
                        db_index=True,
                        max_length=50,
                    ),
                ),
                (
                    "target_type",
                    models.CharField(
                        blank=True,
                        max_length=100,
                    ),
                ),
                (
                    "target_id",
                    models.CharField(
                        blank=True,
                        max_length=80,
                    ),
                ),
                (
                    "target_label",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                    ),
                ),
                (
                    "sensitivity",
                    models.CharField(
                        choices=[
                            ("NORMAL", "Normal"),
                            ("SENSITIVE", "Sensitive"),
                        ],
                        db_index=True,
                        default="NORMAL",
                        max_length=12,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=(
                            django.db.models
                            .deletion.SET_NULL
                        ),
                        related_name=(
                            "audit_actions"
                        ),
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": (
                    "Action Log"
                ),
                "verbose_name_plural": (
                    "Action Logs"
                ),
                "ordering": [
                    "-created_at",
                    "-id",
                ],
            },
        ),
        migrations.AddIndex(
            model_name="actionlog",
            index=models.Index(
                fields=[
                    "action",
                    "created_at",
                ],
                name="audit_action_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actionlog",
            index=models.Index(
                fields=[
                    "module",
                    "created_at",
                ],
                name="audit_module_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actionlog",
            index=models.Index(
                fields=[
                    "actor_role_snapshot",
                    "created_at",
                ],
                name="audit_role_created_idx",
            ),
        ),
    ]
