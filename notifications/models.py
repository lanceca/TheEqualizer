from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_target_roles(value):
    from accounts.models import User
    if (not isinstance(value, list) or len(value) > len(User.Role.values)
            or any(role not in User.Role.values for role in value)):
        raise ValidationError("Choose valid staff roles.")


class SystemUpdate(models.Model):
    class Type(models.TextChoices):
        NEW = "NEW", "New"
        IMPROVED = "IMPROVED", "Improved"
        FIXED = "FIXED", "Fixed"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        IMPORTANT = "IMPORTANT", "Important"

    title = models.CharField(max_length=200)
    version = models.CharField(max_length=60, blank=True)
    summary = models.TextField(max_length=600)
    change_notes = models.TextField()
    update_type = models.CharField(max_length=20, choices=Type.choices, default=Type.IMPROVED)
    target_roles = models.JSONField(default=list, blank=True, validators=[validate_target_roles])
    show_popup = models.BooleanField(default=True)
    require_acknowledgement = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title


class SystemUpdateReceipt(models.Model):
    update = models.ForeignKey(SystemUpdate, related_name="receipts", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    seen_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "update"], name="unique_system_update_receipt")]


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

    def get_notification_type_display(self):
        if self.notification_type == self.Type.DELETION_REQUEST:
            return "Archive Request"
        return dict(self.Type.choices).get(self.notification_type, self.notification_type)
