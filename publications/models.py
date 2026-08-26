from django.core.files.storage import default_storage
from django.db import models


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Article(models.Model):
    class DraftType(models.TextChoices):
        NORMAL = "NORMAL", "Normal Draft"
        EDIT_REQUEST = "EDIT_REQUEST", "Edit Request Draft"

    title = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="articles",
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="articles",
    )

    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="articles",
    )

    content = models.TextField()

    featured_image = models.ImageField(
        upload_to="articles/",
        blank=True,
        null=True,
    )

    draft_type = models.CharField(
        max_length=20,
        choices=DraftType.choices,
        default=DraftType.NORMAL,
    )

    source_article = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="edit_drafts",
    )

    is_published = models.BooleanField(
        default=False,
    )

    is_archived = models.BooleanField(
        default=False,
    )

    archived_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    published_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ArticleAttachment(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    image = models.ImageField(
        upload_to="articles/attachments/",
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.article.title} - Attachment {self.id}"


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REVISION = "REVISION", "Sent Back for Revision"

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    submitted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="submissions",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewer_notes = models.TextField(
        blank=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    resubmission_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="resubmissions",
    )

    # =========================
    # SUBMISSION SNAPSHOT
    # =========================

    snapshot_title = models.CharField(
        max_length=255,
        blank=True,
    )

    snapshot_content = models.TextField(
        blank=True,
    )

    snapshot_category_name = models.CharField(
        max_length=100,
        blank=True,
    )

    snapshot_tags = models.JSONField(
        default=list,
        blank=True,
    )

    snapshot_featured_image = models.CharField(
        max_length=500,
        blank=True,
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return (
            f"{self.snapshot_title or self.article.title} - "
            f"{self.get_status_display()}"
        )

    def capture_article_snapshot(self):
        """
        Capture the article exactly as it exists at the moment
        this Submission is created.
        """

        article = self.article

        self.snapshot_title = article.title
        self.snapshot_content = article.content

        self.snapshot_category_name = (
            article.category.name
            if article.category
            else ""
        )

        self.snapshot_tags = list(
            article.tags.values_list(
                "name",
                flat=True,
            )
        )

        self.snapshot_featured_image = (
            article.featured_image.name
            if article.featured_image
            else ""
        )

        self.save(
            update_fields=[
                "snapshot_title",
                "snapshot_content",
                "snapshot_category_name",
                "snapshot_tags",
                "snapshot_featured_image",
            ]
        )

        # Normally a new Submission has no snapshot attachments.
        # Clearing them here also makes this method safe if it
        # is accidentally called again.
        self.snapshot_attachments.all().delete()

        for attachment in article.attachments.all():
            SubmissionAttachmentSnapshot.objects.create(
                submission=self,
                image=attachment.image.name,
                caption=attachment.caption or "",
            )

    @property
    def snapshot_featured_image_url(self):
        if not self.snapshot_featured_image:
            return ""

        return default_storage.url(
            self.snapshot_featured_image
        )


class SubmissionAttachmentSnapshot(models.Model):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="snapshot_attachments",
    )

    image = models.CharField(
        max_length=500,
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["id"]

    @property
    def image_url(self):
        if not self.image:
            return ""

        return default_storage.url(
            self.image
        )

    def __str__(self):
        return (
            f"Attachment snapshot for "
            f"Submission #{self.submission_id}"
        )


class EditRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        COMPLETED = "COMPLETED", "Completed"

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="edit_requests",
    )

    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="edit_requests",
    )

    draft_article = models.OneToOneField(
        Article,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="originating_edit_request",
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewer_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"{self.get_status_display()}"
        )


class DeletionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )

    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="deletion_requests",
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewer_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"{self.get_status_display()}"
        )


class ContentReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CANCELLED = "CANCELLED", "Cancelled"
        RESOLVED = "RESOLVED", "Resolved"

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="content_reports",
    )

    reported_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="content_reports",
    )

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    staff_notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"{self.get_status_display()}"
        )