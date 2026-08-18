from django.contrib import admin
from .models import (
    Category,
    Tag,
    Article,
    Submission,
    EditRequest,
    DeletionRequest,
    ContentReport,
    ArticleAttachment,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "author",
        "is_published",
        "is_archived",
        "created_at",
    )

    list_filter = (
        "category",
        "is_published",
        "is_archived",
        "created_at",
    )

    search_fields = (
        "title",
        "content",
        "author__username",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "submitted_by",
        "status",
        "submitted_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "submitted_at",
        "reviewed_at",
    )

    search_fields = (
        "article__title",
        "submitted_by__username",
        "reviewer_notes",
    )

@admin.register(EditRequest)
class EditRequestAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "requested_by",
        "status",
        "created_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "created_at",
        "reviewed_at",
    )

    search_fields = (
        "article__title",
        "requested_by__username",
        "reason",
        "reviewer_notes",
    )

@admin.register(DeletionRequest)
class DeletionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "requested_by",
        "status",
        "created_at",
        "reviewed_at",
    )

    list_filter = (
        "status",
        "created_at",
        "reviewed_at",
    )

    search_fields = (
        "article__title",
        "requested_by__username",
        "reason",
        "reviewer_notes",
    )

@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "reported_by",
        "status",
        "created_at",
        "updated_at",
        "resolved_at",
    )

    list_filter = (
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "article__title",
        "reported_by__username",
        "description",
        "staff_notes",
    )

@admin.register(ArticleAttachment)
class ArticleAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "attachment_name",
        "caption",
        "uploaded_at",
    )

    search_fields = (
        "article__title",
        "caption",
    )

    def attachment_name(self, obj):
        return str(obj)

    attachment_name.short_description = "Attachment"