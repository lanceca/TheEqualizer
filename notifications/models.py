from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        SUBMISSION = "SUBMISSION", "Submission"
        EDIT_REQUEST = "EDIT_REQUEST", "Edit Request"
        DELETION_REQUEST = "DELETION_REQUEST", "Deletion Request"
        CONTENT_REPORT = "CONTENT_REPORT", "Content Report"
        REVISION = "REVISION", "Revision"
        GENERAL = "GENERAL", "General"

    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.GENERAL,
    )

    message = models.TextField()

    related_url = models.CharField(
        max_length=500,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.recipient.username} - "
            f"{self.get_notification_type_display()}"
        )