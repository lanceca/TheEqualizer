from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q

from .validators import (
    validate_article_image,
    validate_article_video,
)


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
        EDIT_REQUEST = (
            "EDIT_REQUEST",
            "Edit Request Draft",
        )

    class AttachmentMode(models.TextChoices):
        IMAGE = "IMAGE", "Image Attachments"
        VIDEO = "VIDEO", "Video Attachments"

    title = models.CharField(
        max_length=255,
    )

    subtitle = models.CharField(
        max_length=300,
        blank=True,
    )

    excerpt = models.TextField(
        blank=True,
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

    attachment_mode = models.CharField(
        max_length=10,
        choices=AttachmentMode.choices,
        default=AttachmentMode.IMAGE,
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="articles",
    )

    # ======================================================
    # PRIMARY AUTHOR
    # ======================================================

    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="articles",
    )

    # ======================================================
    # ARTICLE CONTENT
    # ======================================================

    content = models.TextField()

    featured_image = models.ImageField(
        upload_to="articles/",
        blank=True,
        null=True,
        validators=[
            validate_article_image,
        ],
    )

    featured_image_caption = models.CharField(
        max_length=255,
        blank=True,
    )

    featured_image_credit = models.CharField(
        max_length=255,
        blank=True,
    )

    # ======================================================
    # VERSIONING
    # ======================================================

    version_number = models.PositiveIntegerField(
        default=1,
    )

    # ======================================================
    # DRAFT / WORKFLOW TYPE
    # ======================================================

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

    # ======================================================
    # PUBLICATION STATE
    # ======================================================

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

    # ======================================================
    # READER ENGAGEMENT
    # ======================================================

    view_count = models.PositiveBigIntegerField(
        default=0,
    )

    reaction_count = models.PositiveBigIntegerField(
        default=0,
    )

    share_count = models.PositiveBigIntegerField(
        default=0,
    )

    # ======================================================
    # TIMESTAMPS
    # ======================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=~Q(
                    is_published=True,
                    is_archived=True,
                ),
                name=(
                    "article_not_published_and_archived"
                ),
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if (
            self.is_published
            and self.is_archived
        ):
            errors["is_published"] = (
                "An article cannot be published "
                "and archived at the same time."
            )

        if (
            self.draft_type
            == self.DraftType.EDIT_REQUEST
            and not self.source_article_id
        ):
            errors["source_article"] = (
                "An edit-request draft must "
                "reference its original published "
                "article."
            )

        if (
            self.draft_type
            == self.DraftType.NORMAL
            and self.source_article_id
        ):
            errors["source_article"] = (
                "A normal article should not "
                "reference a source article."
            )

        if (
            self.is_published
            and self.draft_type
            == self.DraftType.EDIT_REQUEST
        ):
            errors["draft_type"] = (
                "An edit-request draft cannot "
                "itself be published."
            )

        if (
            self.pk
            and self.source_article_id
            == self.pk
        ):
            errors["source_article"] = (
                "An article cannot use itself "
                "as its source article."
            )

        if self.version_number < 1:
            errors["version_number"] = (
                "Article version numbers must "
                "start at 1."
            )

        if errors:
            raise ValidationError(
                errors
            )

    @property
    def is_normal_article(self):
        return (
            self.draft_type
            == self.DraftType.NORMAL
        )

    @property
    def is_edit_request_draft(self):
        return (
            self.draft_type
            == self.DraftType.EDIT_REQUEST
        )

    def __str__(self):
        return self.title


class ArticleContributor(models.Model):
    class Role(models.TextChoices):
        CO_WRITER = (
            "CO_WRITER",
            "Co-Writer",
        )

        PHOTOGRAPHER = (
            "PHOTOGRAPHER",
            "Photographer",
        )

        PHOTOJOURNALIST = (
            "PHOTOJOURNALIST",
            "Photojournalist",
        )

        CARTOONIST = (
            "CARTOONIST",
            "Cartoonist",
        )

        ILLUSTRATOR = (
            "ILLUSTRATOR",
            "Illustrator",
        )

        VIDEOGRAPHER = (
            "VIDEOGRAPHER",
            "Videographer",
        )

        VIDEO_EDITOR = (
            "VIDEO_EDITOR",
            "Video Editor",
        )

        LAYOUT_ARTIST = (
            "LAYOUT_ARTIST",
            "Layout Artist",
        )

        RESEARCHER = (
            "RESEARCHER",
            "Researcher",
        )

        CONTRIBUTOR = (
            "CONTRIBUTOR",
            "Contributor",
        )

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="contributors",
    )

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="article_contributions",
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "article",
                    "user",
                    "role",
                ],
                name=(
                    "unique_article_contributor_role"
                ),
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if (
            self.article_id
            and self.user_id
            and self.article.author_id
            == self.user_id
        ):
            errors["user"] = (
                "The primary author should not also "
                "be added as an article contributor."
            )

        if errors:
            raise ValidationError(
                errors
            )

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"{self.get_role_display()} - "
            f"{self.user.username}"
        )


class ArticleAttachment(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    image = models.ImageField(
        upload_to="articles/attachments/",
        validators=[
            validate_article_image,
        ],
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    credit = models.CharField(
        max_length=255,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"Attachment {self.id}"
        )


class ArticleVideoAttachment(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="video_attachments",
    )

    video = models.FileField(
        upload_to="articles/video_attachments/",
        validators=[
            validate_article_video,
        ],
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    credit = models.CharField(
        max_length=255,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"Video Attachment {self.id}"
        )


class ArticleVersion(models.Model):
    class ChangeType(models.TextChoices):
        INITIAL_PUBLICATION = (
            "INITIAL_PUBLICATION",
            "Initial Publication",
        )

        DIRECT_EDIT = (
            "DIRECT_EDIT",
            "Direct Edit",
        )

        APPROVED_REVISION = (
            "APPROVED_REVISION",
            "Approved Revision",
        )

        CORRECTIVE_REVISION = (
            "CORRECTIVE_REVISION",
            "Corrective Revision",
        )

        BASELINE = (
            "BASELINE",
            "Existing Published State",
        )

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version_number = models.PositiveIntegerField()

    change_type = models.CharField(
        max_length=30,
        choices=ChangeType.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    subtitle = models.CharField(
        max_length=300,
        blank=True,
    )

    excerpt = models.TextField(
        blank=True,
    )

    content = models.TextField()

    category_name = models.CharField(
        max_length=100,
        blank=True,
    )

    category_slug = models.CharField(
        max_length=100,
        blank=True,
    )

    attachment_mode = models.CharField(
        max_length=10,
        choices=Article.AttachmentMode.choices,
        default=Article.AttachmentMode.IMAGE,
    )

    author_name = models.CharField(
        max_length=255,
        blank=True,
    )

    contributors = models.JSONField(
        default=list,
        blank=True,
    )

    tags = models.JSONField(
        default=list,
        blank=True,
    )

    featured_image = models.CharField(
        max_length=500,
        blank=True,
    )

    featured_image_caption = models.CharField(
        max_length=255,
        blank=True,
    )

    featured_image_credit = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_article_versions",
    )

    created_by_name = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-version_number",
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "article",
                    "version_number",
                ],
                name=(
                    "unique_article_version_number"
                ),
            ),
        ]

    @property
    def featured_image_url(self):
        if not self.featured_image:
            return ""

        return default_storage.url(
            self.featured_image
        )

    def __str__(self):
        return (
            f"{self.article.title} - "
            f"Version {self.version_number}"
        )


class ArticleVersionImageAttachment(
    models.Model
):
    article_version = models.ForeignKey(
        ArticleVersion,
        on_delete=models.CASCADE,
        related_name="image_attachments",
    )

    image = models.CharField(
        max_length=500,
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    credit = models.CharField(
        max_length=255,
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]

    @property
    def image_url(self):
        if not self.image:
            return ""

        return default_storage.url(
            self.image
        )

    def __str__(self):
        return (
            f"Version {self.article_version.version_number} "
            f"image attachment"
        )


class ArticleVersionVideoAttachment(
    models.Model
):
    article_version = models.ForeignKey(
        ArticleVersion,
        on_delete=models.CASCADE,
        related_name="video_attachments",
    )

    video = models.CharField(
        max_length=500,
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    credit = models.CharField(
        max_length=255,
        blank=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]

    @property
    def video_url(self):
        if not self.video:
            return ""

        return default_storage.url(
            self.video
        )

    def __str__(self):
        return (
            f"Version {self.article_version.version_number} "
            f"video attachment"
        )


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = (
            "PENDING",
            "Pending Approval",
        )

        APPROVED = (
            "APPROVED",
            "Approved",
        )

        REJECTED = (
            "REJECTED",
            "Rejected",
        )

        REVISION = (
            "REVISION",
            "Sent Back for Revision",
        )

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

    # ======================================================
    # SUBMISSION SNAPSHOT
    # ======================================================

    snapshot_title = models.CharField(
        max_length=255,
        blank=True,
    )

    snapshot_subtitle = models.CharField(
        max_length=300,
        blank=True,
    )

    snapshot_excerpt = models.TextField(
        blank=True,
    )

    snapshot_content = models.TextField(
        blank=True,
    )

    snapshot_category_name = models.CharField(
        max_length=100,
        blank=True,
    )

    snapshot_attachment_mode = models.CharField(
        max_length=10,
        blank=True,
        default=Article.AttachmentMode.IMAGE,
    )

    snapshot_author_name = models.CharField(
        max_length=255,
        blank=True,
    )

    snapshot_contributors = models.JSONField(
        default=list,
        blank=True,
    )

    snapshot_tags = models.JSONField(
        default=list,
        blank=True,
    )

    snapshot_version_number = (
        models.PositiveIntegerField(
            default=1,
        )
    )

    snapshot_featured_image = (
        models.CharField(
            max_length=500,
            blank=True,
        )
    )

    snapshot_featured_image_caption = (
        models.CharField(
            max_length=255,
            blank=True,
        )
    )

    snapshot_featured_image_credit = (
        models.CharField(
            max_length=255,
            blank=True,
        )
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
        Capture the article exactly as it exists
        when this Submission is created.
        """

        article = self.article

        self.snapshot_title = (
            article.title
        )

        self.snapshot_subtitle = (
            article.subtitle
        )

        self.snapshot_excerpt = (
            article.excerpt
        )

        self.snapshot_content = (
            article.content
        )

        self.snapshot_category_name = (
            article.category.name
            if article.category
            else ""
        )

        self.snapshot_attachment_mode = (
            article.attachment_mode
        )

        self.snapshot_author_name = (
            article.author.username
            if article.author
            else ""
        )

        self.snapshot_contributors = [
            {
                "user_id": contributor.user_id,
                "username": contributor.user.username,
                "role": contributor.role,
                "role_display": (
                    contributor.get_role_display()
                ),
                "display_order": (
                    contributor.display_order
                ),
            }
            for contributor in (
                article.contributors
                .select_related("user")
                .all()
            )
        ]

        self.snapshot_tags = list(
            article.tags.values_list(
                "name",
                flat=True,
            )
        )

        self.snapshot_version_number = (
            article.version_number
        )

        self.snapshot_featured_image = (
            article.featured_image.name
            if article.featured_image
            else ""
        )

        self.snapshot_featured_image_caption = (
            article.featured_image_caption
        )

        self.snapshot_featured_image_credit = (
            article.featured_image_credit
        )

        self.save(
            update_fields=[
                "snapshot_title",
                "snapshot_subtitle",
                "snapshot_excerpt",
                "snapshot_content",
                "snapshot_category_name",
                "snapshot_attachment_mode",
                "snapshot_author_name",
                "snapshot_contributors",
                "snapshot_tags",
                "snapshot_version_number",
                "snapshot_featured_image",
                "snapshot_featured_image_caption",
                "snapshot_featured_image_credit",
            ]
        )

        self.snapshot_attachments.all().delete()

        for attachment in (
            article.attachments.all()
        ):
            SubmissionAttachmentSnapshot.objects.create(
                submission=self,
                image=attachment.image.name,
                caption=(
                    attachment.caption
                    or ""
                ),
                alt_text=(
                    attachment.alt_text
                    or ""
                ),
                credit=(
                    attachment.credit
                    or ""
                ),
            )

        self.snapshot_video_attachments.all().delete()

        for attachment in (
            article.video_attachments.all()
        ):
            SubmissionVideoAttachmentSnapshot.objects.create(
                submission=self,
                video=attachment.video.name,
                caption=(
                    attachment.caption
                    or ""
                ),
                credit=(
                    attachment.credit
                    or ""
                ),
            )

    @property
    def snapshot_featured_image_url(self):
        if not self.snapshot_featured_image:
            return ""

        return default_storage.url(
            self.snapshot_featured_image
        )


class SubmissionAttachmentSnapshot(
    models.Model
):
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

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    credit = models.CharField(
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
            "Attachment snapshot for "
            f"Submission #{self.submission_id}"
        )


class SubmissionVideoAttachmentSnapshot(
    models.Model
):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="snapshot_video_attachments",
    )

    video = models.CharField(
        max_length=500,
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
    )

    credit = models.CharField(
        max_length=255,
        blank=True,
    )

    class Meta:
        ordering = ["id"]

    @property
    def video_url(self):
        if not self.video:
            return ""

        return default_storage.url(
            self.video
        )

    def __str__(self):
        return (
            "Video attachment snapshot for "
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

        REVISION_REQUIRED = (
            "REVISION_REQUIRED",
            "Revision Required",
        )

        CANCELLED = (
            "CANCELLED",
            "Cancelled",
        )

        RESOLVED = (
            "RESOLVED",
            "Resolved",
        )

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
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
    )

    staff_notes = models.TextField(
        blank=True,
    )

    forced_edit_request = models.OneToOneField(
        EditRequest,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="content_report",
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