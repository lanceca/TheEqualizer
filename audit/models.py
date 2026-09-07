from django.conf import settings
from django.db import models


class ActionLog(models.Model):
    class Sensitivity(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        SENSITIVE = "SENSITIVE", "Sensitive"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="audit_actions",
    )

    actor_username_snapshot = models.CharField(
        max_length=150,
        blank=True,
    )

    actor_role_snapshot = models.CharField(
        max_length=30,
        blank=True,
    )

    action = models.CharField(
        max_length=80,
        db_index=True,
    )

    module = models.CharField(
        max_length=50,
        db_index=True,
    )

    target_type = models.CharField(
        max_length=100,
        blank=True,
    )

    target_id = models.CharField(
        max_length=80,
        blank=True,
    )

    target_label = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    sensitivity = models.CharField(
        max_length=12,
        choices=Sensitivity.choices,
        default=Sensitivity.NORMAL,
        db_index=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Action Log"
        verbose_name_plural = "Action Logs"

        indexes = [
            models.Index(
                fields=["action", "created_at"],
                name="audit_action_created_idx",
            ),
            models.Index(
                fields=["module", "created_at"],
                name="audit_module_created_idx",
            ),
            models.Index(
                fields=[
                    "actor_role_snapshot",
                    "created_at",
                ],
                name="audit_role_created_idx",
            ),
        ]

    def __str__(self):
        actor_name = (
            self.actor_username_snapshot
            or "System"
        )

        return (
            f"{actor_name} — "
            f"{self.action} — "
            f"{self.target_label}"
        )
