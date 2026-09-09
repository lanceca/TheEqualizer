from functools import wraps
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from notifications.models import Notification

from .models import (
    AboutUsPage,
    Article,
    ArticleAttachment,
    ArticleContributor,
    ArticleVersion,
    ArticleVersionImageAttachment,
    ArticleVersionVideoAttachment,
    ArticleVideoAttachment,
    Category,
    ContentReport,
    DeletionRequest,
    DigitalPublication,
    EditRequest,
    PeopleProfile,
    SchoolAdvertisement,
    Submission,
    Tag,
)

from .validators import (
    inspect_digital_publication_pdf,
    validate_article_image,
    validate_article_text_fields,
    validate_article_video,
    validate_content_report_description,
)


User = get_user_model()

logger = logging.getLogger(__name__)


# ==========================================================
# ROLE PERMISSION HELPER
# ==========================================================


def publication_role_required(*allowed_roles):
    """
    Require authentication, enforce publication role access,
    and prevent protected staff pages from being cached.
    """

    def decorator(view_func):

        @wraps(view_func)
        @never_cache
        @login_required
        def wrapped_view(request, *args, **kwargs):

            if request.user.role not in allowed_roles:

                return HttpResponseForbidden(
                    "You do not have permission to access this page."
                )

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return wrapped_view

    return decorator


# ==========================================================
# NOTIFICATION HELPERS
# ==========================================================


def notify_user(
    user,
    notification_type,
    message,
    related_url="",
):
    if not user:
        return

    if not user.is_active:
        return

    Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        message=message,
        related_url=related_url,
    )


def notify_eics(
    notification_type,
    message,
    related_url="",
    exclude_user_id=None,
):
    recipients = User.objects.filter(
        role=User.Role.EIC,
        is_active=True,
    )

    if exclude_user_id:

        recipients = recipients.exclude(
            id=exclude_user_id
        )

    for recipient in recipients:

        Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            message=message,
            related_url=related_url,
        )


# ==========================================================
# STORAGE CLEANUP HELPER
# ==========================================================


def delete_storage_file_safely(file_name):
    """
    Best-effort cleanup for media that has already been replaced/deleted
    in the database.

    Supabase/S3 cleanup is deliberately non-fatal: a temporary storage
    outage must not turn an otherwise successful staff action into a 500.
    The failure is still written to the server log for later cleanup.
    """

    if not file_name:
        return True

    try:
        if default_storage.exists(
            file_name
        ):
            default_storage.delete(
                file_name
            )

    except Exception:
        logger.exception(
            (
                "Non-fatal media cleanup failed for "
                "storage object %s."
            ),
            file_name,
        )
        return False

    return True


# ==========================================================
# ARTICLE HELPERS
# ==========================================================


def get_article_attachment_limit():
    return getattr(
        settings,
        "ARTICLE_MAX_ATTACHMENTS",
        15,
    )


def get_article_video_attachment_limit():
    return getattr(
        settings,
        "ARTICLE_MAX_VIDEO_ATTACHMENTS",
        5,
    )


def get_normalized_attachment_mode(
    category,
    requested_mode,
):
    if (
        category.slug == "videos"
        and requested_mode
        == Article.AttachmentMode.VIDEO
    ):
        return Article.AttachmentMode.VIDEO

    return Article.AttachmentMode.IMAGE


CUSTOM_TAG_MAX_COUNT = 10


def get_submitted_custom_tag_names(request):
    """
    Parse custom article tags entered by EICs and Editors.

    Commas and new lines may both be used as separators. Existing tags
    are reused later with a case-insensitive name match.
    """

    raw_value = request.POST.get(
        "custom_tags",
        "",
    )

    normalized_value = (
        raw_value
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", ",")
    )

    tag_name_max_length = (
        Tag._meta
        .get_field("name")
        .max_length
    )

    custom_tag_names = []
    seen_names = set()

    for raw_name in normalized_value.split(","):
        name = " ".join(
            raw_name.split()
        ).strip()

        if not name:
            continue

        if len(name) > tag_name_max_length:
            raise ValidationError(
                (
                    "Custom tags can contain a maximum "
                    f"of {tag_name_max_length} characters each."
                )
            )

        normalized_name = name.casefold()

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)
        custom_tag_names.append(name)

    if len(custom_tag_names) > CUSTOM_TAG_MAX_COUNT:
        raise ValidationError(
            (
                "You can add a maximum of "
                f"{CUSTOM_TAG_MAX_COUNT} custom tags at a time."
            )
        )

    return custom_tag_names


def generate_unique_tag_slug(name):
    """Generate a unique slug for a newly-created reusable tag."""

    max_length = (
        Tag._meta
        .get_field("slug")
        .max_length
    )

    base_slug = slugify(name)

    if not base_slug:
        raise ValidationError(
            (
                f'Custom tag "{name}" cannot be used because '
                "it does not produce a valid URL-safe tag name."
            )
        )

    base_slug = base_slug[:max_length].strip("-")

    if not base_slug:
        raise ValidationError(
            (
                f'Custom tag "{name}" cannot be used because '
                "it does not produce a valid URL-safe tag name."
            )
        )

    candidate = base_slug
    counter = 2

    while Tag.objects.filter(slug=candidate).exists():
        suffix = f"-{counter}"
        candidate = (
            base_slug[: max_length - len(suffix)]
            .rstrip("-")
            + suffix
        )
        counter += 1

    return candidate


def resolve_article_tag_ids(
    selected_tag_ids,
    custom_tag_names,
):
    """Validate selected tags and create/reuse custom tags atomically."""

    normalized_selected_ids = []

    for tag_id in selected_tag_ids:
        try:
            normalized_selected_ids.append(int(tag_id))
        except (TypeError, ValueError) as error:
            raise ValidationError(
                "An invalid article tag was selected."
            ) from error

    normalized_selected_ids = list(
        dict.fromkeys(normalized_selected_ids)
    )

    if normalized_selected_ids:
        existing_selected_ids = set(
            Tag.objects
            .filter(id__in=normalized_selected_ids)
            .values_list("id", flat=True)
        )

        if len(existing_selected_ids) != len(normalized_selected_ids):
            raise ValidationError(
                "One or more selected article tags no longer exist."
            )

    resolved_ids = list(normalized_selected_ids)
    resolved_id_set = set(resolved_ids)

    for name in custom_tag_names:
        tag = (
            Tag.objects
            .filter(name__iexact=name)
            .first()
        )

        if tag is None:
            tag = Tag.objects.create(
                name=name,
                slug=generate_unique_tag_slug(name),
            )

        if tag.id not in resolved_id_set:
            resolved_ids.append(tag.id)
            resolved_id_set.add(tag.id)

    return resolved_ids


def validate_uploaded_article_videos(
    attachments=None,
):
    attachments = attachments or []

    for index, video in enumerate(
        attachments,
        start=1,
    ):
        try:
            validate_article_video(video)

        except ValidationError as error:
            filename = getattr(
                video,
                "name",
                f"Video Attachment {index}",
            )

            raise ValidationError(
                (
                    f'Video "{filename}": '
                    f"{get_validation_error_message(error)}"
                )
            ) from error


def validate_new_video_attachment_count(
    attachments,
):
    maximum = (
        get_article_video_attachment_limit()
    )

    if len(attachments) > maximum:
        raise ValidationError(
            (
                "An article can contain a maximum "
                f"of {maximum} attached videos."
            )
        )


def validate_existing_article_video_attachment_count(
    article,
    new_attachments,
    remove_attachment_ids=None,
):
    maximum = (
        get_article_video_attachment_limit()
    )

    remove_attachment_ids = (
        remove_attachment_ids
        or []
    )

    current_count = (
        article.video_attachments.count()
    )

    removable_count = (
        ArticleVideoAttachment.objects
        .filter(
            article=article,
            id__in=remove_attachment_ids,
        )
        .values("id")
        .distinct()
        .count()
    )

    final_count = (
        current_count
        - removable_count
        + len(new_attachments)
    )

    if final_count > maximum:
        raise ValidationError(
            (
                "An article can contain a maximum "
                f"of {maximum} attached videos. "
                "This change would result in "
                f"{final_count} videos."
            )
        )

    return final_count


def validate_attachment_mode_transition(
    article,
    attachment_mode,
    remove_image_ids=None,
    remove_video_ids=None,
):
    remove_image_ids = remove_image_ids or []
    remove_video_ids = remove_video_ids or []

    remaining_images = (
        ArticleAttachment.objects
        .filter(article=article)
        .exclude(id__in=remove_image_ids)
        .exists()
    )

    remaining_videos = (
        ArticleVideoAttachment.objects
        .filter(article=article)
        .exclude(id__in=remove_video_ids)
        .exists()
    )

    if (
        attachment_mode
        == Article.AttachmentMode.VIDEO
        and remaining_images
    ):
        raise ValidationError(
            (
                "Remove all existing image attachments "
                "before switching to Video Attachments."
            )
        )

    if (
        attachment_mode
        == Article.AttachmentMode.IMAGE
        and remaining_videos
    ):
        raise ValidationError(
            (
                "Remove all existing video attachments "
                "before switching to Image Attachments "
                "or to a non-Videos category."
            )
        )


def get_validation_error_message(error):
    """
    Convert Django ValidationError into a readable message.
    """

    if hasattr(error, "messages"):

        return " ".join(
            str(message)
            for message in error.messages
        )

    return str(error)


def validate_uploaded_article_images(
    featured_image=None,
    attachments=None,
):
    """
    Validate every newly-uploaded image before database
    operations begin.
    """

    attachments = attachments or []

    if featured_image:

        try:

            validate_article_image(
                featured_image
            )

        except ValidationError as error:

            raise ValidationError(
                (
                    "Featured image: "
                    f"{get_validation_error_message(error)}"
                )
            ) from error

    for index, image in enumerate(
        attachments,
        start=1,
    ):

        try:

            validate_article_image(
                image
            )

        except ValidationError as error:

            filename = getattr(
                image,
                "name",
                f"Attachment {index}",
            )

            raise ValidationError(
                (
                    f'Attachment "{filename}": '
                    f"{get_validation_error_message(error)}"
                )
            ) from error


def validate_new_attachment_count(
    attachments,
):
    maximum = get_article_attachment_limit()

    if len(attachments) > maximum:

        raise ValidationError(
            (
                f"An article can contain a maximum "
                f"of {maximum} attached images."
            )
        )


def validate_existing_article_attachment_count(
    article,
    new_attachments,
    remove_attachment_ids=None,
):
    """
    Calculate the attachment total after removals and
    newly-added uploads.
    """

    maximum = get_article_attachment_limit()

    remove_attachment_ids = (
        remove_attachment_ids
        or []
    )

    current_count = (
        article.attachments.count()
    )

    removable_count = (
        ArticleAttachment.objects
        .filter(
            article=article,
            id__in=remove_attachment_ids,
        )
        .values("id")
        .distinct()
        .count()
    )

    final_count = (
        current_count
        - removable_count
        + len(new_attachments)
    )

    if final_count > maximum:

        raise ValidationError(
            (
                f"An article can contain a maximum "
                f"of {maximum} attached images. "
                f"This change would result in "
                f"{final_count} attachments."
            )
        )

    return final_count


# ==========================================================
# CONTRIBUTOR HELPERS
# ==========================================================


def get_available_contributors(
    exclude_user=None,
):
    """
    Return active publication users who may be credited
    as contributors.
    """

    users = User.objects.filter(
        is_active=True,
        role__in=[
            User.Role.EIC,
            User.Role.EDITOR,
            User.Role.STAFF,
        ],
    ).order_by(
        "username"
    )

    if exclude_user:

        users = users.exclude(
            id=exclude_user.id
        )

    return users


def get_contributor_role_choices():
    return ArticleContributor.Role.choices


def get_submitted_contributors(request):
    """
    Read Role + User contributor rows from the form.

    Empty rows are allowed and ignored; partial rows are rejected.
    """

    contributor_roles = request.POST.getlist(
        "contributor_roles"
    )

    contributor_user_ids = request.POST.getlist(
        "contributor_users"
    )

    submitted_contributors = []

    if not (
        contributor_roles
        or contributor_user_ids
    ):

        return submitted_contributors

    if (
        len(contributor_roles)
        != len(contributor_user_ids)
    ):

        raise ValidationError(
            (
                "Contributor information is incomplete. "
                "Each contributor must have both a role "
                "and a publication member selected."
            )
        )

    for role, user_id in zip(
        contributor_roles,
        contributor_user_ids,
    ):

        role = role.strip()
        user_id = user_id.strip()

        if not role and not user_id:
            continue

        if not role or not user_id:

            raise ValidationError(
                (
                    "Each contributor must have both "
                    "a role and a publication member."
                )
            )

        submitted_contributors.append(
            {
                "role": role,
                "user_id": user_id,
            }
        )

    return submitted_contributors


def validate_article_contributors(
    article,
    submitted_contributors,
):
    """
    Validate contributor roles and publication users.
    """

    valid_roles = {
        value
        for value, label
        in ArticleContributor.Role.choices
    }

    normalized = []
    seen_pairs = set()

    for contributor in submitted_contributors:

        role = contributor["role"]
        user_id = contributor["user_id"]

        if role not in valid_roles:

            raise ValidationError(
                "An invalid contributor role was selected."
            )

        try:

            user_id = int(user_id)

        except (
            TypeError,
            ValueError,
        ) as error:

            raise ValidationError(
                "An invalid contributor was selected."
            ) from error

        if user_id == article.author_id:

            raise ValidationError(
                (
                    "The primary author cannot also be "
                    "added as a contributor."
                )
            )

        pair = (
            user_id,
            role,
        )

        if pair in seen_pairs:

            raise ValidationError(
                (
                    "The same person cannot be assigned "
                    "the same contributor role more than once."
                )
            )

        seen_pairs.add(
            pair
        )

        normalized.append(
            {
                "role": role,
                "user_id": user_id,
            }
        )

    valid_user_ids = {
        user.id
        for user in User.objects.filter(
            id__in=[
                contributor["user_id"]
                for contributor in normalized
            ],
            is_active=True,
            role__in=[
                User.Role.EIC,
                User.Role.EDITOR,
                User.Role.STAFF,
            ],
        )
    }

    for contributor in normalized:

        if (
            contributor["user_id"]
            not in valid_user_ids
        ):

            raise ValidationError(
                (
                    "One or more selected contributors "
                    "are not active publication members."
                )
            )

    return normalized


def set_article_contributors(
    article,
    submitted_contributors,
):
    """
    Replace contributor assignments.
    """

    submitted_contributors = (
        validate_article_contributors(
            article,
            submitted_contributors,
        )
    )

    article.contributors.all().delete()

    for display_order, contributor in enumerate(
        submitted_contributors
    ):
        ArticleContributor.objects.create(
            article=article,
            user_id=contributor["user_id"],
            role=contributor["role"],
            display_order=display_order,
        )


def copy_article_contributors(
    source_article,
    destination_article,
):
    """
    Copy contributor credits between article versions.
    """

    destination_article.contributors.all().delete()

    for contributor in (
        source_article.contributors
        .select_related("user")
        .all()
    ):

        ArticleContributor.objects.create(
            article=destination_article,
            user=contributor.user,
            role=contributor.role,
            display_order=contributor.display_order,
        )


# ==========================================================
# GENERAL ARTICLE HELPERS
# ==========================================================


def generate_unique_article_slug(
    title,
    exclude_article_id=None,
    suffix="",
):
    base_slug = slugify(
        title
    ) or "article"

    if suffix:

        base_slug = (
            f"{base_slug}-{suffix}"
        )

    slug = base_slug
    counter = 1

    queryset = Article.objects.all()

    if exclude_article_id:

        queryset = queryset.exclude(
            id=exclude_article_id
        )

    while queryset.filter(
        slug=slug
    ).exists():

        slug = (
            f"{base_slug}-{counter}"
        )

        counter += 1

    return slug


def copy_article_attachments(
    source_article,
    destination_article,
):
    """
    Copy attachment database references to another Article.

    The physical image file is intentionally reused.
    """

    for attachment in source_article.attachments.all():

        ArticleAttachment.objects.create(
            article=destination_article,
            image=attachment.image,
            caption=attachment.caption,
            alt_text=attachment.alt_text,
            credit=attachment.credit,
        )


def replace_article_attachments(
    source_article,
    destination_article,
):
    destination_article.attachments.all().delete()

    copy_article_attachments(
        source_article,
        destination_article,
    )


def copy_article_video_attachments(
    source_article,
    destination_article,
):
    """
    Copy video attachment database references to another Article.
    The physical video file is intentionally reused.
    """

    for attachment in (
        source_article.video_attachments.all()
    ):
        ArticleVideoAttachment.objects.create(
            article=destination_article,
            video=attachment.video,
            caption=attachment.caption,
            credit=attachment.credit,
        )


def replace_article_video_attachments(
    source_article,
    destination_article,
):
    destination_article.video_attachments.all().delete()

    copy_article_video_attachments(
        source_article,
        destination_article,
    )


def build_article_form_context(
    request,
    article=None,
):
    return {
        "article": article,
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "available_contributors": (
            get_available_contributors(
                exclude_user=(
                    article.author
                    if article
                    else request.user
                )
            )
        ),
        "contributor_role_choices": (
            get_contributor_role_choices()
        ),
    }


def capture_article_version(
    article,
    change_type,
    created_by=None,
):
    """
    Persist an immutable snapshot of one official published
    article version.

    If the same article/version was already captured, the
    existing immutable snapshot is returned unchanged.
    """

    existing_version = (
        ArticleVersion.objects
        .filter(
            article=article,
            version_number=article.version_number,
        )
        .first()
    )

    if existing_version:
        return existing_version

    contributors = [
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

    tags = list(
        article.tags.values_list(
            "name",
            flat=True,
        )
    )

    article_version = (
        ArticleVersion.objects.create(
            article=article,
            version_number=(
                article.version_number
            ),
            change_type=change_type,
            title=article.title,
            subtitle=article.subtitle,
            excerpt=article.excerpt,
            content=article.content,
            category_name=(
                article.category.name
                if article.category
                else ""
            ),
            category_slug=(
                article.category.slug
                if article.category
                else ""
            ),
            attachment_mode=(
                article.attachment_mode
            ),
            author_name=(
                article.author.username
                if article.author
                else ""
            ),
            contributors=contributors,
            tags=tags,
            featured_image=(
                article.featured_image.name
                if article.featured_image
                else ""
            ),
            featured_image_caption=(
                article.featured_image_caption
            ),
            featured_image_credit=(
                article.featured_image_credit
            ),
            created_by=created_by,
            created_by_name=(
                created_by.username
                if created_by
                else ""
            ),
        )
    )

    for display_order, attachment in enumerate(
        article.attachments.all()
    ):
        ArticleVersionImageAttachment.objects.create(
            article_version=article_version,
            image=attachment.image.name,
            caption=attachment.caption or "",
            alt_text=attachment.alt_text or "",
            credit=attachment.credit or "",
            display_order=display_order,
        )

    for display_order, attachment in enumerate(
        article.video_attachments.all()
    ):
        ArticleVersionVideoAttachment.objects.create(
            article_version=article_version,
            video=attachment.video.name,
            caption=attachment.caption or "",
            credit=attachment.credit or "",
            display_order=display_order,
        )

    return article_version


def ensure_current_article_version_baseline(
    article,
):
    """
    Preserve the current published state before it is replaced.

    This is mainly for articles that already existed before
    ArticleVersion history was introduced. It captures only the
    current real version and never fabricates older versions.
    """

    if not article.is_published:
        return None

    if ArticleVersion.objects.filter(
        article=article,
        version_number=article.version_number,
    ).exists():
        return None

    return capture_article_version(
        article,
        ArticleVersion.ChangeType.BASELINE,
        created_by=None,
    )


def resolve_eic_direct_revision_reports(
    article,
):
    """
    Resolve revision-required Staff content reports for an
    EIC-authored article after the EIC directly edits it.

    These reports intentionally have no forced EditRequest because
    the EIC may directly manage their own published article.
    """

    reports = (
        ContentReport.objects
        .select_for_update()
        .filter(
            article=article,
            status=ContentReport.Status.REVISION_REQUIRED,
            forced_edit_request__isnull=True,
        )
        .select_related(
            "reported_by"
        )
    )

    resolved_count = 0

    for report in reports:

        report.status = (
            ContentReport.Status.RESOLVED
        )

        report.resolved_at = timezone.now()

        report.save(
            update_fields=[
                "status",
                "resolved_at",
                "updated_at",
            ]
        )

        notify_user(
            report.reported_by,
            Notification.Type.CONTENT_REPORT,
            (
                f'The corrective revision for '
                f'"{article.title}" was completed by '
                f'the Editor in Chief. Your content '
                f'report has been resolved.'
            ),
            reverse(
                "my_content_reports"
            ),
        )

        resolved_count += 1

    return resolved_count


def resolve_reports_after_eic_archive(
    article,
):
    """
    Resolve active Staff reports when an EIC archives their own
    published article. The concern is closed because the reported
    content is no longer publicly published.
    """

    reports = (
        ContentReport.objects
        .select_for_update()
        .filter(
            article=article,
            status__in=[
                ContentReport.Status.OPEN,
                ContentReport.Status.REVISION_REQUIRED,
            ],
        )
        .select_related(
            "reported_by"
        )
    )

    resolved_count = 0

    for report in reports:

        closure_note = (
            "The article was archived by the Editor in Chief. "
            "This report was resolved because the reported "
            "content is no longer publicly published."
        )

        if report.staff_notes:
            report.staff_notes = (
                f"{report.staff_notes}\n\n{closure_note}"
            )
        else:
            report.staff_notes = closure_note

        report.status = (
            ContentReport.Status.RESOLVED
        )

        report.resolved_at = timezone.now()

        report.save(
            update_fields=[
                "status",
                "staff_notes",
                "resolved_at",
                "updated_at",
            ]
        )

        notify_user(
            report.reported_by,
            Notification.Type.CONTENT_REPORT,
            (
                f'"{article.title}" was archived by the '
                f'Editor in Chief. Your content report '
                f'has been resolved.'
            ),
            reverse(
                "my_content_reports"
            ),
        )

        resolved_count += 1

    return resolved_count


# ==========================================================
# ARTICLE CREATION
# ==========================================================


@publication_role_required(
    User.Role.EDITOR,
    User.Role.EIC,
)
def create_article(request):
    categories = Category.objects.all()
    tags = Tag.objects.all()

    available_contributors = (
        get_available_contributors(
            exclude_user=request.user
        )
    )

    context = {
        "categories": categories,
        "tags": tags,
        "available_contributors": (
            available_contributors
        ),
        "contributor_role_choices": (
            get_contributor_role_choices()
        ),
    }

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        subtitle = request.POST.get(
            "subtitle",
            "",
        ).strip()

        excerpt = request.POST.get(
            "excerpt",
            "",
        ).strip()

        category_id = request.POST.get(
            "category"
        )

        content = request.POST.get(
            "content",
            "",
        ).strip()

        tag_ids = request.POST.getlist(
            "tags"
        )

        featured_image_caption = request.POST.get(
            "featured_image_caption",
            "",
        ).strip()

        featured_image_credit = request.POST.get(
            "featured_image_credit",
            "",
        ).strip()


        try:

            validate_article_text_fields(
                title=title,
                subtitle=subtitle,
                excerpt=excerpt,
                content=content,
                featured_image_caption=(
                    featured_image_caption
                ),
                featured_image_credit=(
                    featured_image_credit
                ),
            )

            custom_tag_names = (
                get_submitted_custom_tag_names(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        action = request.POST.get(
            "action"
        )

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        video_attachments = request.FILES.getlist(
            "video_attachments"
        )

        requested_attachment_mode = request.POST.get(
            "attachment_mode",
            Article.AttachmentMode.IMAGE,
        )

        try:

            submitted_contributors = (
                get_submitted_contributors(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        if request.user.role == User.Role.EDITOR:

            allowed_actions = {
                "draft",
                "submit",
            }

        else:

            allowed_actions = {
                "draft",
                "publish",
            }

        if action not in allowed_actions:

            messages.error(
                request,
                "Invalid article action.",
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        attachment_mode = (
            get_normalized_attachment_mode(
                category,
                requested_attachment_mode,
            )
        )

        try:

            validate_uploaded_article_images(
                featured_image=featured_image,
                attachments=(
                    attachments
                    if attachment_mode
                    == Article.AttachmentMode.IMAGE
                    else []
                ),
            )

            if (
                attachment_mode
                == Article.AttachmentMode.VIDEO
            ):
                if attachments:
                    raise ValidationError(
                        (
                            "Image attachments cannot be uploaded "
                            "while Video Attachments is selected."
                        )
                    )

                validate_new_video_attachment_count(
                    video_attachments
                )

                validate_uploaded_article_videos(
                    video_attachments
                )

            else:
                if video_attachments:
                    raise ValidationError(
                        (
                            "Video attachments are only available "
                            "for the Videos category with Video "
                            "Attachments selected."
                        )
                    )

                validate_new_attachment_count(
                    attachments
                )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        try:

            with transaction.atomic():

                slug = generate_unique_article_slug(
                    title
                )

                article = Article.objects.create(
                    title=title,
                    subtitle=subtitle,
                    excerpt=excerpt,
                    slug=slug,
                    category=category,
                    attachment_mode=attachment_mode,
                    author=request.user,
                    content=content,
                    featured_image=featured_image,
                    featured_image_caption=(
                        featured_image_caption
                    ),
                    featured_image_credit=(
                        featured_image_credit
                    ),
                    version_number=1,
                    draft_type=Article.DraftType.NORMAL,
                )

                resolved_tag_ids = (
                    resolve_article_tag_ids(
                        tag_ids,
                        custom_tag_names,
                    )
                )

                article.tags.set(
                    resolved_tag_ids
                )

                set_article_contributors(
                    article,
                    submitted_contributors,
                )

                for image in attachments:

                    ArticleAttachment.objects.create(
                        article=article,
                        image=image,
                    )

                for video in video_attachments:

                    ArticleVideoAttachment.objects.create(
                        article=article,
                        video=video,
                    )

                if (
                    request.user.role
                    == User.Role.EDITOR
                    and action == "submit"
                ):

                    submission = Submission.objects.create(
                        article=article,
                        submitted_by=request.user,
                        status=Submission.Status.PENDING,
                    )

                    submission.capture_article_snapshot()

                    notify_eics(
                        Notification.Type.SUBMISSION,
                        (
                            f'{request.user.username} submitted '
                            f'"{article.title}" for review.'
                        ),
                        reverse(
                            "pending_submissions"
                        ),
                        exclude_user_id=request.user.id,
                    )

                elif (
                    request.user.role
                    == User.Role.EIC
                    and action == "publish"
                ):

                    article.is_published = True
                    article.is_archived = False
                    article.archived_at = None
                    article.published_at = timezone.now()

                    article.save(
                        update_fields=[
                            "is_published",
                            "is_archived",
                            "archived_at",
                            "published_at",
                            "updated_at",
                        ]
                    )

                    capture_article_version(
                        article,
                        (
                            ArticleVersion
                            .ChangeType
                            .INITIAL_PUBLICATION
                        ),
                        created_by=request.user,
                    )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/create_article.html",
                context,
            )

        if (
            request.user.role
            == User.Role.EDITOR
            and action == "submit"
        ):

            messages.success(
                request,
                f'"{article.title}" was submitted for review.',
            )

            return redirect(
                "my_submissions"
            )

        if (
            request.user.role
            == User.Role.EIC
            and action == "publish"
        ):

            messages.success(
                request,
                f'"{article.title}" was published successfully.',
            )

            return redirect(
                "published_articles"
            )

        messages.success(
            request,
            f'"{article.title}" was saved as a draft.',
        )

        return redirect(
            "my_drafts"
        )

    return render(
        request,
        "publications/create_article.html",
        context,
    )


# ==========================================================
# SUBMISSION WORKFLOW
# ==========================================================


@publication_role_required(
    User.Role.EIC
)
def pending_submissions(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    submissions = (
        Submission.objects
        .filter(
            status=Submission.Status.PENDING
        )
        .select_related(
            "article",
            "submitted_by",
            "article__category",
            "article__source_article",
            "article__author",
        )
        .prefetch_related(
            "article__attachments",
            "article__video_attachments",
            "article__tags",
            "article__contributors",
            "article__contributors__user",
            "snapshot_attachments",
            "snapshot_video_attachments",
        )
    )

    if search_query:

        submissions = submissions.filter(
            Q(
                snapshot_title__icontains=search_query
            )
            | Q(
                snapshot_subtitle__icontains=search_query
            )
            | Q(
                snapshot_excerpt__icontains=search_query
            )
            | Q(
                snapshot_content__icontains=search_query
            )
            | Q(
                snapshot_category_name__icontains=search_query
            )
            | Q(
                snapshot_author_name__icontains=search_query
            )
            | Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__excerpt__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                article__tags__name__icontains=search_query
            )
            | Q(
                article__contributors__user__username__icontains=search_query
            )
            | Q(
                article__contributors__role__icontains=search_query
            )
            | Q(
                submitted_by__username__icontains=search_query
            )
        )

    submissions = (
        submissions
        .order_by(
            "-submitted_at"
        )
        .distinct()
    )

    return render(
        request,
        "publications/pending_submissions.html",
        {
            "submissions": submissions,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def review_submission(
    request,
    submission_id,
):
    action = request.POST.get(
        "action"
    )

    reviewer_notes = request.POST.get(
        "reviewer_notes",
        "",
    ).strip()

    if action not in [
        "approve",
        "reject",
        "revision",
    ]:

        messages.error(
            request,
            "Invalid submission review action.",
        )

        return redirect(
            "pending_submissions"
        )

    with transaction.atomic():

        submission = get_object_or_404(
            Submission.objects
            .select_for_update()
            .select_related(
                "article",
                "submitted_by",
            ),
            id=submission_id,
        )

        if (
            submission.status
            != Submission.Status.PENDING
        ):

            messages.warning(
                request,
                "This submission has already been reviewed.",
            )

            return redirect(
                "pending_submissions"
            )

        article = (
            Article.objects
            .select_for_update()
            .prefetch_related(
                "tags",
                "contributors",
                "contributors__user",
                "attachments",
                "video_attachments",
            )
            .get(
                id=submission.article_id
            )
        )

        if action == "approve":

            if (
                article.draft_type
                == Article.DraftType.EDIT_REQUEST
            ):

                if not article.source_article_id:

                    messages.error(
                        request,
                        (
                            "This edit draft is not connected "
                            "to an original article."
                        ),
                    )

                    return redirect(
                        "pending_submissions"
                    )

                original_article = (
                    Article.objects
                    .select_for_update()
                    .prefetch_related(
                        "tags",
                        "contributors",
                        "contributors__user",
                        "attachments",
                    )
                    .get(
                        id=article.source_article_id
                    )
                )

                if (
                    original_article.is_archived
                    or not original_article.is_published
                ):

                    messages.warning(
                        request,
                        (
                            "The original article is no longer "
                            "an active published article."
                        ),
                    )

                    return redirect(
                        "pending_submissions"
                    )

                edit_request = (
                    EditRequest.objects
                    .select_for_update()
                    .filter(
                        draft_article=article,
                        status=EditRequest.Status.APPROVED,
                    )
                    .first()
                )

                if edit_request is None:

                    edit_request = (
                        EditRequest.objects
                        .select_for_update()
                        .filter(
                            article=original_article,
                            requested_by=article.author,
                            status=EditRequest.Status.APPROVED,
                            draft_article__isnull=True,
                        )
                        .order_by(
                            "-reviewed_at",
                            "-created_at",
                        )
                        .first()
                    )

                    if edit_request:

                        edit_request.draft_article = article

                        edit_request.save(
                            update_fields=[
                                "draft_article",
                            ]
                        )

                if edit_request is None:

                    messages.error(
                        request,
                        (
                            "No approved edit request is "
                            "connected to this draft."
                        ),
                    )

                    return redirect(
                        "pending_submissions"
                    )

                ensure_current_article_version_baseline(
                    original_article
                )

                corrective_report_exists = (
                    ContentReport.objects
                    .filter(
                        forced_edit_request=edit_request,
                        status=(
                            ContentReport.Status
                            .REVISION_REQUIRED
                        ),
                    )
                    .exists()
                )

                original_article.title = article.title
                original_article.subtitle = article.subtitle
                original_article.excerpt = article.excerpt

                original_article.slug = (
                    generate_unique_article_slug(
                        article.title,
                        exclude_article_id=original_article.id,
                    )
                )

                original_article.category = article.category
                original_article.content = article.content

                original_article.featured_image = (
                    article.featured_image
                )

                original_article.featured_image_caption = (
                    article.featured_image_caption
                )

                original_article.featured_image_credit = (
                    article.featured_image_credit
                )

                original_article.version_number = max(
                    original_article.version_number + 1,
                    article.version_number,
                )

                original_article.is_published = True
                original_article.is_archived = False
                original_article.archived_at = None

                original_article.save()

                original_article.tags.set(
                    article.tags.all()
                )

                copy_article_contributors(
                    article,
                    original_article,
                )

                replace_article_attachments(
                    article,
                    original_article,
                )

                replace_article_video_attachments(
                    article,
                    original_article,
                )

                original_article.attachment_mode = (
                    article.attachment_mode
                )

                original_article.save(
                    update_fields=[
                        "attachment_mode",
                        "updated_at",
                    ]
                )

                if corrective_report_exists:
                    version_change_type = (
                        ArticleVersion
                        .ChangeType
                        .CORRECTIVE_REVISION
                    )
                else:
                    version_change_type = (
                        ArticleVersion
                        .ChangeType
                        .APPROVED_REVISION
                    )

                capture_article_version(
                    original_article,
                    version_change_type,
                    created_by=request.user,
                )

                submission.status = (
                    Submission.Status.APPROVED
                )

                submission.reviewer_notes = reviewer_notes
                submission.reviewed_at = timezone.now()

                submission.save(
                    update_fields=[
                        "status",
                        "reviewer_notes",
                        "reviewed_at",
                    ]
                )

                edit_request.status = (
                    EditRequest.Status.COMPLETED
                )

                edit_request.save(
                    update_fields=[
                        "status",
                    ]
                )

                notify_user(
                    submission.submitted_by,
                    Notification.Type.REVISION,
                    (
                        f'Your revised version of '
                        f'"{original_article.title}" was '
                        f'approved and is now published '
                        f'as version '
                        f'{original_article.version_number}.'
                    ),
                    reverse(
                        "published_articles"
                    ),
                )

                content_report = (
                    ContentReport.objects
                    .select_for_update()
                    .filter(
                        forced_edit_request=edit_request,
                        status=(
                            ContentReport.Status.REVISION_REQUIRED
                        ),
                    )
                    .select_related(
                        "reported_by"
                    )
                    .first()
                )

                if content_report:

                    content_report.status = (
                        ContentReport.Status.RESOLVED
                    )

                    content_report.resolved_at = timezone.now()

                    content_report.save(
                        update_fields=[
                            "status",
                            "resolved_at",
                            "updated_at",
                        ]
                    )

                    notify_user(
                        content_report.reported_by,
                        Notification.Type.CONTENT_REPORT,
                        (
                            f'The corrective revision for '
                            f'"{original_article.title}" was '
                            f'approved. Your content report '
                            f'has been resolved.'
                        ),
                        reverse(
                            "my_content_reports"
                        ),
                    )

                article.is_archived = True
                article.archived_at = timezone.now()
                article.is_published = False

                article.save(
                    update_fields=[
                        "is_archived",
                        "archived_at",
                        "is_published",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    (
                        f'The revision for '
                        f'"{original_article.title}" '
                        f'was approved and published as '
                        f'version '
                        f'{original_article.version_number}.'
                    ),
                )

                return redirect(
                    "pending_submissions"
                )

            if article.is_archived:

                messages.warning(
                    request,
                    (
                        "This article is archived and cannot "
                        "be approved as a normal submission."
                    ),
                )

                return redirect(
                    "pending_submissions"
                )

            if article.is_published:

                messages.warning(
                    request,
                    "This article is already published.",
                )

                return redirect(
                    "pending_submissions"
                )

            submission.status = (
                Submission.Status.APPROVED
            )

            article.is_published = True
            article.is_archived = False
            article.archived_at = None

            if article.published_at is None:

                article.published_at = timezone.now()

            article.save(
                update_fields=[
                    "is_published",
                    "is_archived",
                    "archived_at",
                    "published_at",
                    "updated_at",
                ]
            )

            capture_article_version(
                article,
                (
                    ArticleVersion
                    .ChangeType
                    .INITIAL_PUBLICATION
                ),
                created_by=request.user,
            )

            submission.reviewer_notes = reviewer_notes
            submission.reviewed_at = timezone.now()

            submission.save(
                update_fields=[
                    "status",
                    "reviewer_notes",
                    "reviewed_at",
                ]
            )

            notify_user(
                submission.submitted_by,
                Notification.Type.SUBMISSION,
                (
                    f'Your submission "{article.title}" '
                    f'was approved and published.'
                ),
                reverse(
                    "my_submissions"
                ),
            )

            messages.success(
                request,
                (
                    f'"{article.title}" was approved '
                    f'and published.'
                ),
            )

            return redirect(
                "pending_submissions"
            )

        if action == "reject":

            submission.status = (
                Submission.Status.REJECTED
            )

            submission.reviewer_notes = reviewer_notes
            submission.reviewed_at = timezone.now()

            submission.save(
                update_fields=[
                    "status",
                    "reviewer_notes",
                    "reviewed_at",
                ]
            )

            if (
                article.draft_type
                == Article.DraftType.EDIT_REQUEST
            ):
                edit_request = (
                    EditRequest.objects
                    .select_for_update()
                    .filter(
                        draft_article=article,
                        status=EditRequest.Status.APPROVED,
                    )
                    .first()
                )

                if edit_request is not None:
                    edit_request.status = (
                        EditRequest.Status.REJECTED
                    )

                    edit_request.save(
                        update_fields=[
                            "status",
                        ]
                    )

                article.is_archived = True
                article.archived_at = timezone.now()
                article.is_published = False

                article.save(
                    update_fields=[
                        "is_archived",
                        "archived_at",
                        "is_published",
                        "updated_at",
                    ]
                )

                if article.source_article:
                    rejected_title = (
                        article.source_article.title
                    )
                else:
                    rejected_title = article.title

                notify_user(
                    submission.submitted_by,
                    Notification.Type.REVISION,
                    (
                        f'Your revised version of '
                        f'"{rejected_title}" was '
                        f'rejected by the EIC.'
                    ),
                    reverse(
                        "my_edit_requests"
                    ),
                )

            else:
                notify_user(
                    submission.submitted_by,
                    Notification.Type.SUBMISSION,
                    (
                        f'Your submission "{article.title}" '
                        f'was rejected by the EIC.'
                    ),
                    reverse(
                        "my_submissions"
                    ),
                )

            messages.warning(
                request,
                f'"{article.title}" was rejected.',
            )


        elif action == "revision":

            submission.status = (
                Submission.Status.REVISION
            )

            submission.reviewer_notes = reviewer_notes
            submission.reviewed_at = timezone.now()

            submission.save(
                update_fields=[
                    "status",
                    "reviewer_notes",
                    "reviewed_at",
                ]
            )

            notify_user(
                submission.submitted_by,
                Notification.Type.REVISION,
                (
                    f'The EIC requested revisions for '
                    f'"{article.title}".'
                ),
                reverse(
                    "my_submissions"
                ),
            )

            messages.info(
                request,
                (
                    f'Revisions were requested for '
                    f'"{article.title}".'
                ),
            )

    return redirect(
        "pending_submissions"
    )


@publication_role_required(
    User.Role.EDITOR
)
def my_submissions(request):
    selected_status = (
        request.GET.get(
            "status",
            "ALL",
        )
        .strip()
        .upper()
    )

    valid_statuses = {
        "ALL",
        Submission.Status.PENDING,
        Submission.Status.REVISION,
        Submission.Status.APPROVED,
        Submission.Status.REJECTED,
    }

    if selected_status not in valid_statuses:
        selected_status = "ALL"

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    # My Submissions contains only non-resubmitted root submissions.
    # Once a root submission receives a resubmission child, the revision
    # chain moves exclusively to Resubmitted Submissions.
    submissions = (
        Submission.objects
        .filter(
            submitted_by=request.user,
            resubmission_of__isnull=True,
            resubmissions__isnull=True,
        )
        .exclude(
            article__edit_requests__status__in=[
                EditRequest.Status.APPROVED,
                EditRequest.Status.COMPLETED,
            ]
        )
        .select_related(
            "article",
            "article__category",
            "article__source_article",
            "article__author",
        )
        .prefetch_related(
            "article__attachments",
            "article__video_attachments",
            "article__tags",
            "article__contributors",
            "article__contributors__user",
            "snapshot_attachments",
            "snapshot_video_attachments",
        )
    )

    if selected_status != "ALL":
        submissions = submissions.filter(
            status=selected_status
        )

    if search_query:
        submissions = submissions.filter(
            Q(
                snapshot_title__icontains=search_query
            )
            | Q(
                snapshot_subtitle__icontains=search_query
            )
            | Q(
                snapshot_excerpt__icontains=search_query
            )
            | Q(
                snapshot_content__icontains=search_query
            )
            | Q(
                snapshot_category_name__icontains=search_query
            )
            | Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__excerpt__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                article__tags__name__icontains=search_query
            )
            | Q(
                article__contributors__user__username__icontains=search_query
            )
            | Q(
                article__contributors__role__icontains=search_query
            )
        )

    submissions = (
        submissions
        .order_by(
            "-submitted_at"
        )
        .distinct()
    )

    return render(
        request,
        "publications/my_submissions.html",
        {
            "submissions": submissions,
            "selected_status": selected_status,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EDITOR
)
def revise_submission(
    request,
    submission_id,
):
    submission = get_object_or_404(
        Submission.objects
        .select_related(
            "article",
            "article__category",
            "article__author",
        )
        .prefetch_related(
            "article__attachments",
            "article__video_attachments",
            "article__tags",
            "article__contributors",
            "article__contributors__user",
            "snapshot_attachments",
            "snapshot_video_attachments",
        ),
        id=submission_id,
        submitted_by=request.user,
    )

    if (
        submission.status
        != Submission.Status.REVISION
    ):

        messages.warning(
            request,
            (
                "This submission is not currently "
                "available for revision."
            ),
        )

        return redirect(
            "my_submissions"
        )

    if submission.resubmissions.exists():

        messages.warning(
            request,
            (
                "This submission has already been "
                "revised and resubmitted."
            ),
        )

        return redirect(
            "my_submissions"
        )

    article = submission.article

    categories = Category.objects.all()
    tags = Tag.objects.all()

    available_contributors = (
        get_available_contributors(
            exclude_user=article.author
        )
    )

    context = {
        "submission": submission,
        "article": article,
        "categories": categories,
        "tags": tags,
        "available_contributors": (
            available_contributors
        ),
        "contributor_role_choices": (
            get_contributor_role_choices()
        ),
    }

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        subtitle = request.POST.get(
            "subtitle",
            "",
        ).strip()

        excerpt = request.POST.get(
            "excerpt",
            "",
        ).strip()

        category_id = request.POST.get(
            "category"
        )

        content = request.POST.get(
            "content",
            "",
        ).strip()

        tag_ids = request.POST.getlist(
            "tags"
        )

        featured_image_caption = request.POST.get(
            "featured_image_caption",
            "",
        ).strip()

        featured_image_credit = request.POST.get(
            "featured_image_credit",
            "",
        ).strip()


        try:

            validate_article_text_fields(
                title=title,
                subtitle=subtitle,
                excerpt=excerpt,
                content=content,
                featured_image_caption=(
                    featured_image_caption
                ),
                featured_image_credit=(
                    featured_image_credit
                ),
            )

            custom_tag_names = (
                get_submitted_custom_tag_names(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/revise_submission.html",
                context,
            )

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        video_attachments = request.FILES.getlist(
            "video_attachments"
        )

        remove_attachment_ids = (
            request.POST.getlist(
                "remove_attachments"
            )
        )

        remove_video_attachment_ids = (
            request.POST.getlist(
                "remove_video_attachments"
            )
        )

        requested_attachment_mode = request.POST.get(
            "attachment_mode",
            article.attachment_mode,
        )

        try:

            submitted_contributors = (
                get_submitted_contributors(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/revise_submission.html",
                context,
            )

        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/revise_submission.html",
                context,
            )

        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/revise_submission.html",
                context,
            )

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        attachment_mode = (
            get_normalized_attachment_mode(
                category,
                requested_attachment_mode,
            )
        )

        try:

            validate_uploaded_article_images(
                featured_image=featured_image,
                attachments=(
                    attachments
                    if attachment_mode
                    == Article.AttachmentMode.IMAGE
                    else []
                ),
            )

            if (
                attachment_mode
                == Article.AttachmentMode.VIDEO
            ):
                if attachments:
                    raise ValidationError(
                        (
                            "Image attachments cannot be uploaded "
                            "while Video Attachments is selected."
                        )
                    )

                validate_uploaded_article_videos(
                    video_attachments
                )

                validate_existing_article_video_attachment_count(
                    article,
                    video_attachments,
                    remove_video_attachment_ids,
                )

            else:
                if video_attachments:
                    raise ValidationError(
                        (
                            "Video attachments are only available "
                            "for the Videos category with Video "
                            "Attachments selected."
                        )
                    )

                validate_attachment_mode_transition(
                    article,
                    attachment_mode,
                    remove_attachment_ids,
                    remove_video_attachment_ids,
                )

                if (
                    attachment_mode
                    == Article.AttachmentMode.VIDEO
                ):
                    validate_existing_article_video_attachment_count(
                        article,
                        video_attachments,
                        remove_video_attachment_ids,
                    )
                else:
                    validate_existing_article_attachment_count(
                        article,
                        attachments,
                        remove_attachment_ids,
                    )

            validate_attachment_mode_transition(
                article,
                attachment_mode,
                remove_attachment_ids,
                remove_video_attachment_ids,
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/revise_submission.html",
                context,
            )

        try:

            with transaction.atomic():

                locked_submission = get_object_or_404(
                    Submission.objects
                    .select_for_update(),
                    id=submission.id,
                    submitted_by=request.user,
                )

                if (
                    locked_submission.status
                    != Submission.Status.REVISION
                ):

                    messages.warning(
                        request,
                        (
                            "This submission is no longer "
                            "available for revision."
                        ),
                    )

                    return redirect(
                        "my_submissions"
                    )

                if (
                    locked_submission
                    .resubmissions
                    .exists()
                ):

                    messages.warning(
                        request,
                        (
                            "This submission has already "
                            "been revised and resubmitted."
                        ),
                    )

                    return redirect(
                        "my_submissions"
                    )

                article = (
                    Article.objects
                    .select_for_update()
                    .get(
                        id=locked_submission.article_id
                    )
                )

                validate_existing_article_attachment_count(
                    article,
                    attachments,
                    remove_attachment_ids,
                )

                slug = generate_unique_article_slug(
                    title,
                    exclude_article_id=article.id,
                )

                article.title = title
                article.subtitle = subtitle
                article.excerpt = excerpt
                article.slug = slug
                article.category = category
                article.attachment_mode = attachment_mode
                article.content = content

                article.featured_image_caption = (
                    featured_image_caption
                )

                article.featured_image_credit = (
                    featured_image_credit
                )

                if featured_image:

                    article.featured_image = (
                        featured_image
                    )

                article.save()

                resolved_tag_ids = (
                    resolve_article_tag_ids(
                        tag_ids,
                        custom_tag_names,
                    )
                )

                article.tags.set(
                    resolved_tag_ids
                )

                set_article_contributors(
                    article,
                    submitted_contributors,
                )

                if remove_attachment_ids:

                    ArticleAttachment.objects.filter(
                        article=article,
                        id__in=remove_attachment_ids,
                    ).delete()

                if remove_video_attachment_ids:

                    ArticleVideoAttachment.objects.filter(
                        article=article,
                        id__in=remove_video_attachment_ids,
                    ).delete()

                for image in attachments:

                    ArticleAttachment.objects.create(
                        article=article,
                        image=image,
                    )

                for video in video_attachments:

                    ArticleVideoAttachment.objects.create(
                        article=article,
                        video=video,
                    )

                new_submission = (
                    Submission.objects.create(
                        article=article,
                        submitted_by=request.user,
                        status=Submission.Status.PENDING,
                        resubmission_of=locked_submission,
                    )
                )

                new_submission.capture_article_snapshot()

                notify_eics(
                    Notification.Type.REVISION,
                    (
                        f'{request.user.username} resubmitted '
                        f'"{article.title}" after revision.'
                    ),
                    reverse(
                        "pending_submissions"
                    ),
                    exclude_user_id=request.user.id,
                )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/revise_submission.html",
                context,
            )

        messages.success(
            request,
            (
                f'"{article.title}" was revised '
                f'and resubmitted successfully.'
            ),
        )

        return redirect(
            "resubmitted_submissions"
        )

    return render(
        request,
        "publications/revise_submission.html",
        context,
    )


@publication_role_required(
    User.Role.EDITOR
)
def resubmitted_submissions(request):
    selected_scope = (
        request.GET.get(
            "scope",
            "ALL",
        )
        .strip()
        .upper()
    )

    if selected_scope not in {
        "ALL",
        "CURRENT",
        "HISTORY",
    }:
        selected_scope = "ALL"

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    submissions = (
        Submission.objects
        .filter(
            submitted_by=request.user,
            resubmission_of__isnull=False,
        )
        .select_related(
            "article",
            "article__category",
            "article__author",
            "resubmission_of",
        )
        .prefetch_related(
            "article__attachments",
            "article__video_attachments",
            "article__tags",
            "article__contributors",
            "article__contributors__user",
            "snapshot_attachments",
            "snapshot_video_attachments",
            "resubmission_of__snapshot_attachments",
            "resubmissions",
        )
    )

    if selected_scope == "CURRENT":
        # Only the latest unresolved record in each resubmission chain.
        submissions = submissions.filter(
            resubmissions__isnull=True,
            status__in=[
                Submission.Status.PENDING,
                Submission.Status.REVISION,
            ],
        )

    elif selected_scope == "HISTORY":
        # Completed records plus older revision records superseded by
        # a newer resubmission belong to History.
        submissions = submissions.filter(
            Q(
                status__in=[
                    Submission.Status.APPROVED,
                    Submission.Status.REJECTED,
                ]
            )
            | Q(
                resubmissions__isnull=False
            )
        )

    if search_query:
        submissions = submissions.filter(
            Q(
                snapshot_title__icontains=search_query
            )
            | Q(
                snapshot_subtitle__icontains=search_query
            )
            | Q(
                snapshot_excerpt__icontains=search_query
            )
            | Q(
                snapshot_content__icontains=search_query
            )
            | Q(
                snapshot_category_name__icontains=search_query
            )
            | Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__excerpt__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                resubmission_of__reviewer_notes__icontains=search_query
            )
        )

    submissions = (
        submissions
        .order_by(
            "-submitted_at"
        )
        .distinct()
    )

    return render(
        request,
        "publications/resubmitted_submissions.html",
        {
            "submissions": submissions,
            "selected_scope": selected_scope,
            "search_query": search_query,
        },
    )


# ==========================================================
# DRAFTS
# ==========================================================


@publication_role_required(
    User.Role.EDITOR,
    User.Role.EIC,
)
def my_drafts(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    drafts = (
        Article.objects
        .filter(
            author=request.user,
            is_published=False,
            is_archived=False,
            submissions__isnull=True,
        )
        .select_related(
            "category",
            "source_article",
            "author",
        )
        .prefetch_related(
            "attachments",
            "video_attachments",
            "tags",
            "contributors",
            "contributors__user",
        )
    )

    if request.user.role == User.Role.EIC:

        drafts = drafts.filter(
            draft_type=Article.DraftType.NORMAL
        )

    if search_query:

        drafts = drafts.filter(
            Q(
                title__icontains=search_query
            )
            | Q(
                subtitle__icontains=search_query
            )
            | Q(
                excerpt__icontains=search_query
            )
            | Q(
                content__icontains=search_query
            )
            | Q(
                category__name__icontains=search_query
            )
            | Q(
                tags__name__icontains=search_query
            )
            | Q(
                contributors__user__username__icontains=search_query
            )
            | Q(
                contributors__role__icontains=search_query
            )
        )

    drafts = (
        drafts
        .order_by(
            "-updated_at"
        )
        .distinct()
    )

    normal_drafts = drafts.filter(
        draft_type=Article.DraftType.NORMAL
    )

    if request.user.role == User.Role.EDITOR:

        edit_request_drafts = drafts.filter(
            draft_type=Article.DraftType.EDIT_REQUEST
        )

    else:

        edit_request_drafts = (
            Article.objects.none()
        )

    return render(
        request,
        "publications/my_drafts.html",
        {
            "drafts": drafts,
            "normal_drafts": normal_drafts,
            "edit_request_drafts": (
                edit_request_drafts
            ),
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EDITOR,
    User.Role.EIC,
)
def edit_draft(
    request,
    article_id,
):
    article = get_object_or_404(
        Article.objects
        .select_related(
            "category",
            "source_article",
            "author",
        )
        .prefetch_related(
            "attachments",
            "video_attachments",
            "tags",
            "contributors",
            "contributors__user",
        ),
        id=article_id,
        author=request.user,
        is_published=False,
        is_archived=False,
        submissions__isnull=True,
    )

    if (
        request.user.role == User.Role.EIC
        and article.draft_type
        != Article.DraftType.NORMAL
    ):

        return HttpResponseForbidden(
            (
                "The EIC cannot directly manage "
                "Editor edit-request drafts."
            )
        )

    if (
        article.draft_type
        == Article.DraftType.EDIT_REQUEST
    ):

        approved_request_exists = (
            EditRequest.objects.filter(
                article=article.source_article,
                requested_by=request.user,
                status=EditRequest.Status.APPROVED,
                draft_article=article,
            ).exists()
        )

        if not approved_request_exists:

            messages.warning(
                request,
                (
                    "This edit-request draft "
                    "is no longer available."
                ),
            )

            return redirect(
                "my_drafts"
            )

    categories = Category.objects.all()
    tags = Tag.objects.all()

    available_contributors = (
        get_available_contributors(
            exclude_user=article.author
        )
    )

    context = {
        "article": article,
        "categories": categories,
        "tags": tags,
        "available_contributors": (
            available_contributors
        ),
        "contributor_role_choices": (
            get_contributor_role_choices()
        ),
    }

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        subtitle = request.POST.get(
            "subtitle",
            "",
        ).strip()

        excerpt = request.POST.get(
            "excerpt",
            "",
        ).strip()

        category_id = request.POST.get(
            "category"
        )

        content = request.POST.get(
            "content",
            "",
        ).strip()

        tag_ids = request.POST.getlist(
            "tags"
        )

        featured_image_caption = request.POST.get(
            "featured_image_caption",
            "",
        ).strip()

        featured_image_credit = request.POST.get(
            "featured_image_credit",
            "",
        ).strip()


        try:

            validate_article_text_fields(
                title=title,
                subtitle=subtitle,
                excerpt=excerpt,
                content=content,
                featured_image_caption=(
                    featured_image_caption
                ),
                featured_image_credit=(
                    featured_image_credit
                ),
            )

            custom_tag_names = (
                get_submitted_custom_tag_names(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_draft.html",
                context,
            )

        action = request.POST.get(
            "action"
        )

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        video_attachments = request.FILES.getlist(
            "video_attachments"
        )

        remove_attachment_ids = (
            request.POST.getlist(
                "remove_attachments"
            )
        )

        remove_video_attachment_ids = (
            request.POST.getlist(
                "remove_video_attachments"
            )
        )

        requested_attachment_mode = request.POST.get(
            "attachment_mode",
            article.attachment_mode,
        )

        try:

            submitted_contributors = (
                get_submitted_contributors(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_draft.html",
                context,
            )

        if request.user.role == User.Role.EDITOR:

            allowed_actions = {
                "draft",
                "save",
                "submit",
            }

        else:

            allowed_actions = {
                "draft",
                "save",
                "publish",
            }

        if action not in allowed_actions:

            messages.error(
                request,
                "Invalid draft action.",
            )

            return redirect(
                "my_drafts"
            )

        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/edit_draft.html",
                context,
            )

        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/edit_draft.html",
                context,
            )

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        attachment_mode = (
            get_normalized_attachment_mode(
                category,
                requested_attachment_mode,
            )
        )

        try:

            validate_uploaded_article_images(
                featured_image=featured_image,
                attachments=(
                    attachments
                    if attachment_mode
                    == Article.AttachmentMode.IMAGE
                    else []
                ),
            )

            if (
                attachment_mode
                == Article.AttachmentMode.VIDEO
            ):
                if attachments:
                    raise ValidationError(
                        (
                            "Image attachments cannot be uploaded "
                            "while Video Attachments is selected."
                        )
                    )

                validate_uploaded_article_videos(
                    video_attachments
                )

                validate_existing_article_video_attachment_count(
                    article,
                    video_attachments,
                    remove_video_attachment_ids,
                )

            else:
                if video_attachments:
                    raise ValidationError(
                        (
                            "Video attachments are only available "
                            "for the Videos category with Video "
                            "Attachments selected."
                        )
                    )

                validate_existing_article_attachment_count(
                    article,
                    attachments,
                    remove_attachment_ids,
                )

            validate_attachment_mode_transition(
                article,
                attachment_mode,
                remove_attachment_ids,
                remove_video_attachment_ids,
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_draft.html",
                context,
            )

        try:

            with transaction.atomic():

                locked_article = get_object_or_404(
                    Article.objects
                    .select_for_update()
                    .select_related(
                        "author",
                    ),
                    id=article.id,
                    author=request.user,
                )

                if (
                    locked_article.is_published
                    or locked_article.is_archived
                    or locked_article.submissions.exists()
                ):

                    messages.warning(
                        request,
                        (
                            "This draft is no longer "
                            "available for editing."
                        ),
                    )

                    return redirect(
                        "my_drafts"
                    )

                if (
                    request.user.role
                    == User.Role.EIC
                    and locked_article.draft_type
                    != Article.DraftType.NORMAL
                ):

                    return HttpResponseForbidden(
                        (
                            "The EIC cannot directly manage "
                            "Editor edit-request drafts."
                        )
                    )

                if (
                    locked_article.draft_type
                    == Article.DraftType.EDIT_REQUEST
                ):

                    approved_request_exists = (
                        EditRequest.objects.filter(
                            article=(
                                locked_article.source_article
                            ),
                            requested_by=request.user,
                            status=(
                                EditRequest.Status.APPROVED
                            ),
                            draft_article=locked_article,
                        ).exists()
                    )

                    if not approved_request_exists:

                        messages.warning(
                            request,
                            (
                                "The approved edit request "
                                "for this draft is no longer active."
                            ),
                        )

                        return redirect(
                            "my_drafts"
                        )

                validate_attachment_mode_transition(
                    locked_article,
                    attachment_mode,
                    remove_attachment_ids,
                    remove_video_attachment_ids,
                )

                if (
                    attachment_mode
                    == Article.AttachmentMode.VIDEO
                ):
                    validate_existing_article_video_attachment_count(
                        locked_article,
                        video_attachments,
                        remove_video_attachment_ids,
                    )
                else:
                    validate_existing_article_attachment_count(
                        locked_article,
                        attachments,
                        remove_attachment_ids,
                    )

                suffix = ""

                if (
                    locked_article.draft_type
                    == Article.DraftType.EDIT_REQUEST
                ):

                    suffix = (
                        f"edit-draft-{locked_article.id}"
                    )

                slug = generate_unique_article_slug(
                    title,
                    exclude_article_id=(
                        locked_article.id
                    ),
                    suffix=suffix,
                )

                locked_article.title = title
                locked_article.subtitle = subtitle
                locked_article.excerpt = excerpt
                locked_article.slug = slug
                locked_article.category = category
                locked_article.attachment_mode = attachment_mode
                locked_article.content = content

                locked_article.featured_image_caption = (
                    featured_image_caption
                )

                locked_article.featured_image_credit = (
                    featured_image_credit
                )

                if featured_image:

                    locked_article.featured_image = (
                        featured_image
                    )

                locked_article.save()

                resolved_tag_ids = (
                    resolve_article_tag_ids(
                        tag_ids,
                        custom_tag_names,
                    )
                )

                locked_article.tags.set(
                    resolved_tag_ids
                )

                set_article_contributors(
                    locked_article,
                    submitted_contributors,
                )

                if remove_attachment_ids:

                    ArticleAttachment.objects.filter(
                        article=locked_article,
                        id__in=remove_attachment_ids,
                    ).delete()

                if remove_video_attachment_ids:

                    ArticleVideoAttachment.objects.filter(
                        article=locked_article,
                        id__in=remove_video_attachment_ids,
                    ).delete()

                for image in attachments:

                    ArticleAttachment.objects.create(
                        article=locked_article,
                        image=image,
                    )

                for video in video_attachments:

                    ArticleVideoAttachment.objects.create(
                        article=locked_article,
                        video=video,
                    )

                if (
                    request.user.role
                    == User.Role.EDITOR
                    and action == "submit"
                ):

                    submission = (
                        Submission.objects.create(
                            article=locked_article,
                            submitted_by=request.user,
                            status=Submission.Status.PENDING,
                        )
                    )

                    submission.capture_article_snapshot()

                    if (
                        locked_article.draft_type
                        == Article.DraftType.EDIT_REQUEST
                    ):

                        notification_type = (
                            Notification.Type.REVISION
                        )

                        notification_message = (
                            f'{request.user.username} submitted '
                            f'a revised version of '
                            f'"{locked_article.source_article.title}" '
                            f'for review.'
                        )

                    else:

                        notification_type = (
                            Notification.Type.SUBMISSION
                        )

                        notification_message = (
                            f'{request.user.username} submitted '
                            f'"{locked_article.title}" for review.'
                        )

                    notify_eics(
                        notification_type,
                        notification_message,
                        reverse(
                            "pending_submissions"
                        ),
                        exclude_user_id=request.user.id,
                    )

                elif (
                    request.user.role
                    == User.Role.EIC
                    and action == "publish"
                ):

                    locked_article.is_published = True
                    locked_article.is_archived = False
                    locked_article.archived_at = None

                    if locked_article.published_at is None:

                        locked_article.published_at = (
                            timezone.now()
                        )

                    locked_article.save(
                        update_fields=[
                            "is_published",
                            "is_archived",
                            "archived_at",
                            "published_at",
                            "updated_at",
                        ]
                    )

                    capture_article_version(
                        locked_article,
                        (
                            ArticleVersion
                            .ChangeType
                            .INITIAL_PUBLICATION
                        ),
                        created_by=request.user,
                    )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_draft.html",
                context,
            )

        if (
            request.user.role
            == User.Role.EDITOR
            and action == "submit"
        ):

            messages.success(
                request,
                (
                    f'"{locked_article.title}" '
                    f'was submitted for review.'
                ),
            )

            return redirect(
                "my_submissions"
            )

        if (
            request.user.role
            == User.Role.EIC
            and action == "publish"
        ):

            messages.success(
                request,
                (
                    f'"{locked_article.title}" '
                    f'was published successfully.'
                ),
            )

            return redirect(
                "published_articles"
            )

        messages.success(
            request,
            (
                f'"{locked_article.title}" '
                f'was saved successfully.'
            ),
        )

        return redirect(
            "my_drafts"
        )

    return render(
        request,
        "publications/edit_draft.html",
        context,
    )


@publication_role_required(
    User.Role.EDITOR,
    User.Role.EIC,
)
@require_POST
def delete_draft(
    request,
    article_id,
):
    with transaction.atomic():

        article = get_object_or_404(
            Article.objects
            .select_for_update(),
            id=article_id,
            author=request.user,
            draft_type=Article.DraftType.NORMAL,
        )

        if (
            article.is_published
            or article.is_archived
            or article.submissions.exists()
        ):

            messages.warning(
                request,
                (
                    "This article is no longer "
                    "an undeclared draft."
                ),
            )

            return redirect(
                "my_drafts"
            )

        title = article.title

        article.delete()

    messages.warning(
        request,
        f'Draft "{title}" was deleted.',
    )

    return redirect(
        "my_drafts"
    )


# ==========================================================
# PUBLISHED ARTICLES
# ==========================================================


@publication_role_required(
    User.Role.EDITOR,
    User.Role.EIC,
    User.Role.STAFF,
)
def published_articles(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    articles = (
        Article.objects
        .filter(
            is_published=True,
            is_archived=False,
            draft_type=Article.DraftType.NORMAL,
        )
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "attachments",
            "video_attachments",
            "tags",
            "contributors",
            "contributors__user",
        )
    )

    if request.user.role == User.Role.EDITOR:

        articles = articles.filter(
            author=request.user
        )

    if search_query:

        articles = articles.filter(
            Q(
                title__icontains=search_query
            )
            | Q(
                subtitle__icontains=search_query
            )
            | Q(
                excerpt__icontains=search_query
            )
            | Q(
                content__icontains=search_query
            )
            | Q(
                category__name__icontains=search_query
            )
            | Q(
                tags__name__icontains=search_query
            )
            | Q(
                author__username__icontains=search_query
            )
            | Q(
                contributors__user__username__icontains=search_query
            )
            | Q(
                contributors__role__icontains=search_query
            )
        )

    articles = (
        articles
        .order_by(
            "-published_at"
        )
        .distinct()
    )

    return render(
        request,
        "publications/published_articles.html",
        {
            "articles": articles,
            "search_query": search_query,
        },
    )


# ==========================================================
# ARTICLE VERSION HISTORY
# ==========================================================


def get_version_history_article_for_user(
    request,
    article_id,
):
    """
    Return a normal article that the current role may inspect
    in version history.

    EIC:
    - may inspect currently published normal articles;
    - may also inspect archived normal articles.

    Staff:
    - may inspect currently published normal articles only.

    Editor:
    - may inspect only their own currently published normal articles.

    Adviser access remains intentionally excluded.
    """

    queryset = (
        Article.objects
        .filter(
            id=article_id,
            draft_type=Article.DraftType.NORMAL,
        )
        .select_related(
            "category",
            "author",
        )
    )

    if request.user.role == User.Role.EIC:

        queryset = queryset.filter(
            Q(
                is_published=True,
                is_archived=False,
            )
            |
            Q(
                is_published=False,
                is_archived=True,
            )
        )

    elif request.user.role == User.Role.EDITOR:

        queryset = queryset.filter(
            author=request.user,
            is_published=True,
            is_archived=False,
        )

    elif request.user.role == User.Role.STAFF:

        queryset = queryset.filter(
            is_published=True,
            is_archived=False,
        )

    else:

        queryset = Article.objects.none()

    return get_object_or_404(
        queryset
    )


@publication_role_required(
    User.Role.EIC,
    User.Role.EDITOR,
    User.Role.STAFF,
)
def article_version_history(
    request,
    article_id,
):
    article = (
        get_version_history_article_for_user(
            request,
            article_id,
        )
    )

    versions = (
        ArticleVersion.objects
        .filter(
            article=article
        )
        .select_related(
            "created_by"
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )

    return render(
        request,
        "publications/article_version_history.html",
        {
            "article": article,
            "versions": versions,
        },
    )


@publication_role_required(
    User.Role.EIC,
    User.Role.EDITOR,
    User.Role.STAFF,
)
def article_version_detail(
    request,
    article_id,
    version_number,
):
    article = (
        get_version_history_article_for_user(
            request,
            article_id,
        )
    )

    article_version = get_object_or_404(
        ArticleVersion.objects
        .filter(
            article=article,
            version_number=version_number,
        )
        .select_related(
            "created_by"
        )
        .prefetch_related(
            "image_attachments",
            "video_attachments",
        )
    )

    return render(
        request,
        "publications/article_version_detail.html",
        {
            "article": article,
            "article_version": article_version,
        },
    )


# ==========================================================
# EIC DIRECT PUBLISHED ARTICLE MANAGEMENT
# ==========================================================


@publication_role_required(
    User.Role.EIC
)
def edit_published_article(
    request,
    article_id,
):
    article = get_object_or_404(
        Article.objects
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "attachments",
            "video_attachments",
            "tags",
            "contributors",
            "contributors__user",
        ),
        id=article_id,
        author=request.user,
        is_published=True,
        is_archived=False,
        draft_type=Article.DraftType.NORMAL,
    )

    categories = Category.objects.all()
    tags = Tag.objects.all()

    available_contributors = (
        get_available_contributors(
            exclude_user=article.author
        )
    )

    context = {
        "article": article,
        "categories": categories,
        "tags": tags,
        "available_contributors": (
            available_contributors
        ),
        "contributor_role_choices": (
            get_contributor_role_choices()
        ),
    }

    resolved_report_count = 0

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        subtitle = request.POST.get(
            "subtitle",
            "",
        ).strip()

        excerpt = request.POST.get(
            "excerpt",
            "",
        ).strip()

        category_id = request.POST.get(
            "category"
        )

        content = request.POST.get(
            "content",
            "",
        ).strip()

        tag_ids = request.POST.getlist(
            "tags"
        )

        featured_image_caption = request.POST.get(
            "featured_image_caption",
            "",
        ).strip()

        featured_image_credit = request.POST.get(
            "featured_image_credit",
            "",
        ).strip()


        try:

            validate_article_text_fields(
                title=title,
                subtitle=subtitle,
                excerpt=excerpt,
                content=content,
                featured_image_caption=(
                    featured_image_caption
                ),
                featured_image_credit=(
                    featured_image_credit
                ),
            )

            custom_tag_names = (
                get_submitted_custom_tag_names(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_published_article.html",
                context,
            )

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        video_attachments = request.FILES.getlist(
            "video_attachments"
        )

        remove_attachment_ids = (
            request.POST.getlist(
                "remove_attachments"
            )
        )

        remove_video_attachment_ids = (
            request.POST.getlist(
                "remove_video_attachments"
            )
        )

        requested_attachment_mode = request.POST.get(
            "attachment_mode",
            article.attachment_mode,
        )

        try:

            submitted_contributors = (
                get_submitted_contributors(
                    request
                )
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_published_article.html",
                context,
            )

        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/edit_published_article.html",
                context,
            )

        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/edit_published_article.html",
                context,
            )

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        attachment_mode = (
            get_normalized_attachment_mode(
                category,
                requested_attachment_mode,
            )
        )

        try:

            validate_uploaded_article_images(
                featured_image=featured_image,
                attachments=(
                    attachments
                    if attachment_mode
                    == Article.AttachmentMode.IMAGE
                    else []
                ),
            )

            if (
                attachment_mode
                == Article.AttachmentMode.VIDEO
            ):
                if attachments:
                    raise ValidationError(
                        (
                            "Image attachments cannot be uploaded "
                            "while Video Attachments is selected."
                        )
                    )

                validate_uploaded_article_videos(
                    video_attachments
                )

                validate_existing_article_video_attachment_count(
                    article,
                    video_attachments,
                    remove_video_attachment_ids,
                )

            else:
                if video_attachments:
                    raise ValidationError(
                        (
                            "Video attachments are only available "
                            "for the Videos category with Video "
                            "Attachments selected."
                        )
                    )

                validate_attachment_mode_transition(
                    article,
                    attachment_mode,
                    remove_attachment_ids,
                    remove_video_attachment_ids,
                )

                if (
                    attachment_mode
                    == Article.AttachmentMode.VIDEO
                ):
                    validate_existing_article_video_attachment_count(
                        article,
                        video_attachments,
                        remove_video_attachment_ids,
                    )
                else:
                    validate_existing_article_attachment_count(
                        article,
                        attachments,
                        remove_attachment_ids,
                    )

            validate_attachment_mode_transition(
                article,
                attachment_mode,
                remove_attachment_ids,
                remove_video_attachment_ids,
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_published_article.html",
                context,
            )

        try:

            with transaction.atomic():

                article = get_object_or_404(
                    Article.objects
                    .select_for_update(),
                    id=article_id,
                    author=request.user,
                )

                if (
                    not article.is_published
                    or article.is_archived
                    or article.draft_type
                    != Article.DraftType.NORMAL
                ):

                    messages.warning(
                        request,
                        (
                            "This article is no longer "
                            "available for direct editing."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                open_content_report_exists = (
                    ContentReport.objects.filter(
                        article=article,
                        status=ContentReport.Status.OPEN,
                    ).exists()
                )

                if open_content_report_exists:

                    messages.warning(
                        request,
                        (
                            "This article has an open Staff "
                            "content report. Review the report "
                            "before directly editing the article."
                        ),
                    )

                    return redirect(
                        "eic_content_reports"
                    )

                validate_existing_article_attachment_count(
                    article,
                    attachments,
                    remove_attachment_ids,
                )

                ensure_current_article_version_baseline(
                    article
                )

                slug = generate_unique_article_slug(
                    title,
                    exclude_article_id=article.id,
                )

                article.title = title
                article.subtitle = subtitle
                article.excerpt = excerpt
                article.slug = slug
                article.category = category
                article.attachment_mode = attachment_mode
                article.content = content

                article.featured_image_caption = (
                    featured_image_caption
                )

                article.featured_image_credit = (
                    featured_image_credit
                )

                if featured_image:

                    article.featured_image = (
                        featured_image
                    )

                article.version_number += 1

                article.save()

                resolved_tag_ids = (
                    resolve_article_tag_ids(
                        tag_ids,
                        custom_tag_names,
                    )
                )

                article.tags.set(
                    resolved_tag_ids
                )

                set_article_contributors(
                    article,
                    submitted_contributors,
                )

                if remove_attachment_ids:

                    ArticleAttachment.objects.filter(
                        article=article,
                        id__in=remove_attachment_ids,
                    ).delete()

                if remove_video_attachment_ids:

                    ArticleVideoAttachment.objects.filter(
                        article=article,
                        id__in=remove_video_attachment_ids,
                    ).delete()

                for image in attachments:

                    ArticleAttachment.objects.create(
                        article=article,
                        image=image,
                    )

                for video in video_attachments:

                    ArticleVideoAttachment.objects.create(
                        article=article,
                        video=video,
                    )

                resolved_report_count = (
                    resolve_eic_direct_revision_reports(
                        article
                    )
                )

                if resolved_report_count:
                    version_change_type = (
                        ArticleVersion
                        .ChangeType
                        .CORRECTIVE_REVISION
                    )
                else:
                    version_change_type = (
                        ArticleVersion
                        .ChangeType
                        .DIRECT_EDIT
                    )

                capture_article_version(
                    article,
                    version_change_type,
                    created_by=request.user,
                )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/edit_published_article.html",
                context,
            )

        if resolved_report_count:

            messages.success(
                request,
                (
                    f'"{article.title}" was updated '
                    f'successfully and is now version '
                    f'{article.version_number}. '
                    f'{resolved_report_count} corrective '
                    f'content report(s) were resolved.'
                ),
            )

        else:

            messages.success(
                request,
                (
                    f'"{article.title}" was updated '
                    f'successfully and is now version '
                    f'{article.version_number}.'
                ),
            )

        return redirect(
            "published_articles"
        )

    return render(
        request,
        "publications/edit_published_article.html",
        context,
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def archive_own_published_article(
    request,
    article_id,
):
    with transaction.atomic():

        article = get_object_or_404(
            Article.objects
            .select_for_update(),
            id=article_id,
            author=request.user,
            draft_type=Article.DraftType.NORMAL,
        )

        if article.is_archived:

            messages.warning(
                request,
                "This article is already archived.",
            )

            return redirect(
                "published_articles"
            )

        if not article.is_published:

            messages.warning(
                request,
                "This article is no longer published.",
            )

            return redirect(
                "published_articles"
            )

        article.is_published = False
        article.is_archived = True
        article.archived_at = timezone.now()

        article.save(
            update_fields=[
                "is_published",
                "is_archived",
                "archived_at",
                "updated_at",
            ]
        )

        resolved_report_count = (
            resolve_reports_after_eic_archive(
                article
            )
        )

    if resolved_report_count:

        messages.warning(
            request,
            (
                f'"{article.title}" was removed from publication '
                f'and moved to the archive. '
                f'{resolved_report_count} active content '
                f'report(s) were resolved.'
            ),
        )

        return redirect(
            "published_articles"
        )

    messages.warning(
        request,
        (
            f'"{article.title}" was removed from publication '
            f'and moved to the archive.'
        ),
    )

    return redirect(
        "published_articles"
    )


# ==========================================================
# EDIT REQUEST WORKFLOW
# ==========================================================


@publication_role_required(
    User.Role.EDITOR
)
def request_article_edit(
    request,
    article_id,
):
    article = get_object_or_404(
        Article,
        id=article_id,
        author=request.user,
        is_published=True,
        is_archived=False,
        draft_type=Article.DraftType.NORMAL,
    )

    existing_request = EditRequest.objects.filter(
        article=article,
        requested_by=request.user,
        status__in=[
            EditRequest.Status.PENDING,
            EditRequest.Status.APPROVED,
        ],
    ).exists()

    if existing_request:

        messages.warning(
            request,
            (
                "You already have an active edit "
                "request for this article."
            ),
        )

        return redirect(
            "published_articles"
        )

    pending_deletion_request = (
        DeletionRequest.objects.filter(
            article=article,
            requested_by=request.user,
            status=DeletionRequest.Status.PENDING,
        ).exists()
    )

    if pending_deletion_request:

        messages.warning(
            request,
            (
                "You cannot request an edit while a deletion "
                "request is pending for this article."
            ),
        )

        return redirect(
            "published_articles"
        )

    if request.method == "POST":

        reason = request.POST.get(
            "reason",
            "",
        ).strip()

        if not reason:

            messages.error(
                request,
                (
                    "Please provide a reason "
                    "for the edit request."
                ),
            )

        else:

            with transaction.atomic():

                locked_article = get_object_or_404(
                    Article.objects
                    .select_for_update(),
                    id=article.id,
                    author=request.user,
                )

                if (
                    not locked_article.is_published
                    or locked_article.is_archived
                    or locked_article.draft_type
                    != Article.DraftType.NORMAL
                ):

                    messages.warning(
                        request,
                        (
                            "This article is no longer "
                            "available for an edit request."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                existing_request = (
                    EditRequest.objects.filter(
                        article=locked_article,
                        requested_by=request.user,
                        status__in=[
                            EditRequest.Status.PENDING,
                            EditRequest.Status.APPROVED,
                        ],
                    ).exists()
                )

                if existing_request:

                    messages.warning(
                        request,
                        (
                            "You already have an active edit "
                            "request for this article."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                pending_deletion_request = (
                    DeletionRequest.objects.filter(
                        article=locked_article,
                        requested_by=request.user,
                        status=(
                            DeletionRequest.Status.PENDING
                        ),
                    ).exists()
                )

                if pending_deletion_request:

                    messages.warning(
                        request,
                        (
                            "A deletion request is currently "
                            "pending for this article."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                EditRequest.objects.create(
                    article=locked_article,
                    requested_by=request.user,
                    reason=reason,
                )

                notify_eics(
                    Notification.Type.EDIT_REQUEST,
                    (
                        f'{request.user.username} requested '
                        f'permission to edit '
                        f'"{locked_article.title}".'
                    ),
                    reverse(
                        "eic_edit_requests"
                    ),
                    exclude_user_id=request.user.id,
                )

            messages.success(
                request,
                (
                    f'Your edit request for '
                    f'"{locked_article.title}" was submitted.'
                ),
            )

            return redirect(
                "my_edit_requests"
            )

    return render(
        request,
        "publications/request_article_edit.html",
        {
            "article": article,
        },
    )


@publication_role_required(
    User.Role.EDITOR
)
def my_edit_requests(request):
    selected_scope = (
        request.GET.get(
            "scope",
            "ALL",
        )
        .strip()
        .upper()
    )

    if selected_scope not in {
        "ALL",
        "CURRENT",
        "HISTORY",
    }:
        selected_scope = "ALL"

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    requests = (
        EditRequest.objects
        .filter(
            requested_by=request.user
        )
        .select_related(
            "article",
            "article__category",
            "draft_article",
        )
        .annotate(
            draft_has_submission=Exists(
                Submission.objects.filter(
                    article_id=OuterRef(
                        "draft_article_id"
                    )
                )
            )
        )
    )

    if selected_scope == "CURRENT":
        requests = requests.filter(
            status__in=[
                EditRequest.Status.PENDING,
                EditRequest.Status.APPROVED,
            ]
        )

    elif selected_scope == "HISTORY":
        requests = requests.filter(
            status__in=[
                EditRequest.Status.REJECTED,
                EditRequest.Status.COMPLETED,
            ]
        )

    if search_query:
        requests = requests.filter(
            Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                reason__icontains=search_query
            )
            | Q(
                reviewer_notes__icontains=search_query
            )
        )

    requests = requests.order_by(
        "-created_at"
    )

    return render(
        request,
        "publications/my_edit_requests.html",
        {
            "edit_requests": requests,
            "selected_scope": selected_scope,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
def eic_edit_requests(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    requests = (
        EditRequest.objects
        .filter(
            status=EditRequest.Status.PENDING
        )
        .select_related(
            "article",
            "article__category",
            "requested_by",
            "draft_article",
        )
        .order_by(
            "-created_at"
        )
    )

    if search_query:

        requests = requests.filter(
            Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                requested_by__username__icontains=search_query
            )
            | Q(
                reason__icontains=search_query
            )
        )

    return render(
        request,
        "publications/eic_edit_requests.html",
        {
            "edit_requests": requests,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def review_edit_request(
    request,
    request_id,
):
    action = request.POST.get(
        "action"
    )

    reviewer_notes = request.POST.get(
        "reviewer_notes",
        "",
    ).strip()

    if action not in [
        "approve",
        "reject",
    ]:

        messages.error(
            request,
            "Invalid edit request action.",
        )

        return redirect(
            "eic_edit_requests"
        )

    with transaction.atomic():

        edit_request = get_object_or_404(
            EditRequest.objects
            .select_for_update()
            .select_related(
                "article",
                "requested_by",
            ),
            id=request_id,
        )

        if (
            edit_request.status
            != EditRequest.Status.PENDING
        ):

            messages.warning(
                request,
                (
                    "This edit request has already "
                    "been reviewed."
                ),
            )

            return redirect(
                "eic_edit_requests"
            )

        original_article = (
            Article.objects
            .select_for_update()
            .prefetch_related(
                "tags",
                "contributors",
                "contributors__user",
                "attachments",
                "video_attachments",
            )
            .get(
                id=edit_request.article_id
            )
        )

        if (
            not original_article.is_published
            or original_article.is_archived
            or original_article.draft_type
            != Article.DraftType.NORMAL
        ):

            messages.warning(
                request,
                (
                    "The article is no longer available "
                    "for this edit request."
                ),
            )

            return redirect(
                "eic_edit_requests"
            )

        if action == "approve":

            existing_draft = (
                Article.objects.filter(
                    source_article=original_article,
                    draft_type=(
                        Article.DraftType.EDIT_REQUEST
                    ),
                    is_published=False,
                    is_archived=False,
                ).exists()
            )

            if existing_draft:

                messages.warning(
                    request,
                    (
                        "An active edit-request draft already "
                        "exists for this article."
                    ),
                )

                return redirect(
                    "eic_edit_requests"
                )

            pending_deletion = (
                DeletionRequest.objects.filter(
                    article=original_article,
                    status=(
                        DeletionRequest.Status.PENDING
                    ),
                ).exists()
            )

            if pending_deletion:

                messages.warning(
                    request,
                    (
                        "This edit request cannot be approved "
                        "while a deletion request is pending."
                    ),
                )

                return redirect(
                    "eic_edit_requests"
                )

            edit_draft_slug = (
                generate_unique_article_slug(
                    original_article.title,
                    suffix=(
                        f"edit-{edit_request.id}"
                    ),
                )
            )

            edit_draft = Article.objects.create(
                title=original_article.title,
                subtitle=original_article.subtitle,
                excerpt=original_article.excerpt,
                slug=edit_draft_slug,
                category=original_article.category,
                attachment_mode=original_article.attachment_mode,
                author=original_article.author,
                content=original_article.content,
                featured_image=(
                    original_article.featured_image
                ),
                featured_image_caption=(
                    original_article
                    .featured_image_caption
                ),
                featured_image_credit=(
                    original_article
                    .featured_image_credit
                ),
                version_number=(
                    original_article.version_number
                    + 1
                ),
                draft_type=(
                    Article.DraftType.EDIT_REQUEST
                ),
                source_article=original_article,
                is_published=False,
                is_archived=False,
            )

            edit_draft.tags.set(
                original_article.tags.all()
            )

            copy_article_contributors(
                original_article,
                edit_draft,
            )

            copy_article_attachments(
                original_article,
                edit_draft,
            )

            copy_article_video_attachments(
                original_article,
                edit_draft,
            )

            edit_request.status = (
                EditRequest.Status.APPROVED
            )

            edit_request.reviewer_notes = (
                reviewer_notes
            )

            edit_request.reviewed_at = (
                timezone.now()
            )

            edit_request.draft_article = (
                edit_draft
            )

            edit_request.save()

            notify_user(
                edit_request.requested_by,
                Notification.Type.EDIT_REQUEST,
                (
                    f'Your edit request for '
                    f'"{original_article.title}" was approved. '
                    f'A revision draft for version '
                    f'{edit_draft.version_number} '
                    f'is now available.'
                ),
                reverse(
                    "my_drafts"
                ),
            )

            messages.success(
                request,
                (
                    f'The edit request for '
                    f'"{original_article.title}" was approved.'
                ),
            )

        elif action == "reject":

            edit_request.status = (
                EditRequest.Status.REJECTED
            )

            edit_request.reviewer_notes = (
                reviewer_notes
            )

            edit_request.reviewed_at = (
                timezone.now()
            )

            edit_request.save(
                update_fields=[
                    "status",
                    "reviewer_notes",
                    "reviewed_at",
                ]
            )

            notify_user(
                edit_request.requested_by,
                Notification.Type.EDIT_REQUEST,
                (
                    f'Your edit request for '
                    f'"{original_article.title}" was rejected.'
                ),
                reverse(
                    "my_edit_requests"
                ),
            )

            messages.warning(
                request,
                (
                    f'The edit request for '
                    f'"{original_article.title}" was rejected.'
                ),
            )

    return redirect(
        "eic_edit_requests"
    )


# ==========================================================
# DELETION REQUEST WORKFLOW
# ==========================================================


@publication_role_required(
    User.Role.EDITOR
)
def request_article_deletion(
    request,
    article_id,
):
    article = get_object_or_404(
        Article.objects.select_related(
            "category",
            "author",
        ),
        id=article_id,
        author=request.user,
        is_published=True,
        is_archived=False,
        draft_type=Article.DraftType.NORMAL,
    )

    existing_request = (
        DeletionRequest.objects.filter(
            article=article,
            requested_by=request.user,
            status=DeletionRequest.Status.PENDING,
        ).exists()
    )

    if existing_request:

        messages.warning(
            request,
            (
                "You already have a pending deletion "
                "request for this article."
            ),
        )

        return redirect(
            "published_articles"
        )

    active_edit_request = (
        EditRequest.objects.filter(
            article=article,
            requested_by=request.user,
            status__in=[
                EditRequest.Status.PENDING,
                EditRequest.Status.APPROVED,
            ],
        ).exists()
    )

    if active_edit_request:

        messages.warning(
            request,
            (
                "You cannot request deletion while an edit "
                "request is active for this article."
            ),
        )

        return redirect(
            "published_articles"
        )

    if request.method == "POST":

        reason = request.POST.get(
            "reason",
            "",
        ).strip()

        if not reason:

            messages.error(
                request,
                (
                    "Please provide a reason "
                    "for the deletion request."
                ),
            )

        else:

            with transaction.atomic():

                locked_article = get_object_or_404(
                    Article.objects
                    .select_for_update(),
                    id=article.id,
                    author=request.user,
                )

                if (
                    not locked_article.is_published
                    or locked_article.is_archived
                    or locked_article.draft_type
                    != Article.DraftType.NORMAL
                ):

                    messages.warning(
                        request,
                        (
                            "This article is no longer available "
                            "for a deletion request."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                existing_request = (
                    DeletionRequest.objects.filter(
                        article=locked_article,
                        requested_by=request.user,
                        status=(
                            DeletionRequest.Status.PENDING
                        ),
                    ).exists()
                )

                if existing_request:

                    messages.warning(
                        request,
                        (
                            "You already have a pending deletion "
                            "request for this article."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                active_edit_request = (
                    EditRequest.objects.filter(
                        article=locked_article,
                        status__in=[
                            EditRequest.Status.PENDING,
                            EditRequest.Status.APPROVED,
                        ],
                    ).exists()
                )

                if active_edit_request:

                    messages.warning(
                        request,
                        (
                            "An edit request is currently "
                            "active for this article."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                DeletionRequest.objects.create(
                    article=locked_article,
                    requested_by=request.user,
                    reason=reason,
                    status=DeletionRequest.Status.PENDING,
                )

                notify_eics(
                    Notification.Type.DELETION_REQUEST,
                    (
                        f'{request.user.username} requested '
                        f'deletion of '
                        f'"{locked_article.title}".'
                    ),
                    reverse(
                        "eic_deletion_requests"
                    ),
                    exclude_user_id=request.user.id,
                )

            messages.success(
                request,
                (
                    f'Your deletion request for '
                    f'"{locked_article.title}" was submitted.'
                ),
            )

            return redirect(
                "my_deletion_requests"
            )

    return render(
        request,
        "publications/request_article_deletion.html",
        {
            "article": article,
        },
    )


@publication_role_required(
    User.Role.EDITOR
)
def my_deletion_requests(request):
    selected_scope = (
        request.GET.get(
            "scope",
            "ALL",
        )
        .strip()
        .upper()
    )

    if selected_scope not in {
        "ALL",
        "CURRENT",
        "HISTORY",
    }:
        selected_scope = "ALL"

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    requests = (
        DeletionRequest.objects
        .filter(
            requested_by=request.user
        )
        .select_related(
            "article",
            "article__category",
        )
    )

    if selected_scope == "CURRENT":
        requests = requests.filter(
            status=DeletionRequest.Status.PENDING
        )

    elif selected_scope == "HISTORY":
        requests = requests.filter(
            status__in=[
                DeletionRequest.Status.APPROVED,
                DeletionRequest.Status.REJECTED,
            ]
        )

    if search_query:
        requests = requests.filter(
            Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                reason__icontains=search_query
            )
            | Q(
                reviewer_notes__icontains=search_query
            )
        )

    requests = requests.order_by(
        "-created_at"
    )

    return render(
        request,
        "publications/my_deletion_requests.html",
        {
            "deletion_requests": requests,
            "selected_scope": selected_scope,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
def eic_deletion_requests(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    requests = (
        DeletionRequest.objects
        .filter(
            status=DeletionRequest.Status.PENDING
        )
        .select_related(
            "article",
            "article__category",
            "article__author",
            "requested_by",
        )
    )

    if search_query:

        requests = requests.filter(
            Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                requested_by__username__icontains=search_query
            )
            | Q(
                reason__icontains=search_query
            )
        )

    requests = requests.order_by(
        "-created_at"
    )

    return render(
        request,
        "publications/eic_deletion_requests.html",
        {
            "deletion_requests": requests,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def review_deletion_request(
    request,
    request_id,
):
    action = request.POST.get(
        "action"
    )

    reviewer_notes = request.POST.get(
        "reviewer_notes",
        "",
    ).strip()

    if action not in [
        "approve",
        "reject",
    ]:

        messages.error(
            request,
            "Invalid deletion request action.",
        )

        return redirect(
            "eic_deletion_requests"
        )

    with transaction.atomic():

        deletion_request = get_object_or_404(
            DeletionRequest.objects
            .select_for_update()
            .select_related(
                "article",
                "requested_by",
            ),
            id=request_id,
        )

        if (
            deletion_request.status
            != DeletionRequest.Status.PENDING
        ):

            messages.warning(
                request,
                (
                    "This deletion request has already "
                    "been reviewed."
                ),
            )

            return redirect(
                "eic_deletion_requests"
            )

        article = (
            Article.objects
            .select_for_update()
            .get(
                id=deletion_request.article_id
            )
        )

        if action == "approve":

            if article.is_archived:

                messages.warning(
                    request,
                    "This article is already archived.",
                )

                return redirect(
                    "eic_deletion_requests"
                )

            if not article.is_published:

                messages.warning(
                    request,
                    (
                        "This article is no longer "
                        "published."
                    ),
                )

                return redirect(
                    "eic_deletion_requests"
                )

            active_edit_request = (
                EditRequest.objects.filter(
                    article=article,
                    status__in=[
                        EditRequest.Status.PENDING,
                        EditRequest.Status.APPROVED,
                    ],
                ).exists()
            )

            if active_edit_request:

                messages.warning(
                    request,
                    (
                        "This deletion request cannot be "
                        "approved while an edit request "
                        "is active for the article."
                    ),
                )

                return redirect(
                    "eic_deletion_requests"
                )

            article.is_published = False
            article.is_archived = True
            article.archived_at = timezone.now()

            article.save(
                update_fields=[
                    "is_published",
                    "is_archived",
                    "archived_at",
                    "updated_at",
                ]
            )

            deletion_request.status = (
                DeletionRequest.Status.APPROVED
            )

            deletion_request.reviewer_notes = (
                reviewer_notes
            )

            deletion_request.reviewed_at = (
                timezone.now()
            )

            deletion_request.save(
                update_fields=[
                    "status",
                    "reviewer_notes",
                    "reviewed_at",
                ]
            )

            notify_user(
                deletion_request.requested_by,
                Notification.Type.DELETION_REQUEST,
                (
                    f'Your deletion request for '
                    f'"{article.title}" was approved. '
                    f'The article has been archived.'
                ),
                reverse(
                    "my_deletion_requests"
                ),
            )

            messages.success(
                request,
                (
                    f'"{article.title}" was '
                    f'archived successfully.'
                ),
            )

        elif action == "reject":

            deletion_request.status = (
                DeletionRequest.Status.REJECTED
            )

            deletion_request.reviewer_notes = (
                reviewer_notes
            )

            deletion_request.reviewed_at = (
                timezone.now()
            )

            deletion_request.save(
                update_fields=[
                    "status",
                    "reviewer_notes",
                    "reviewed_at",
                ]
            )

            notify_user(
                deletion_request.requested_by,
                Notification.Type.DELETION_REQUEST,
                (
                    f'Your deletion request for '
                    f'"{article.title}" was rejected.'
                ),
                reverse(
                    "my_deletion_requests"
                ),
            )

            messages.warning(
                request,
                (
                    f'The deletion request for '
                    f'"{article.title}" was rejected.'
                ),
            )

    return redirect(
        "eic_deletion_requests"
    )


# ==========================================================
# STAFF CONTENT REPORT WORKFLOW
# ==========================================================


@publication_role_required(
    User.Role.STAFF
)
def report_article_content(
    request,
    article_id,
):
    article = get_object_or_404(
        Article.objects.select_related(
            "category",
            "author",
        ),
        id=article_id,
        is_published=True,
        is_archived=False,
        draft_type=Article.DraftType.NORMAL,
    )

    existing_report = (
        ContentReport.objects.filter(
            article=article,
            reported_by=request.user,
            status__in=[
                ContentReport.Status.OPEN,
                ContentReport.Status.REVISION_REQUIRED,
            ],
        ).exists()
    )

    if existing_report:

        messages.warning(
            request,
            (
                "You already have an active report "
                "for this article."
            ),
        )

        return redirect(
            "my_content_reports"
        )

    if request.method == "POST":

        description = request.POST.get(
            "description",
            "",
        ).strip()


        try:

            validate_content_report_description(
                description
            )

        except ValidationError as error:

            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                "publications/report_article_content.html",
                {
                    "article": article,
                },
            )

        if not description:

            messages.error(
                request,
                (
                    "Please describe the content concern "
                    "before submitting."
                ),
            )

        else:

            with transaction.atomic():

                locked_article = get_object_or_404(
                    Article.objects
                    .select_for_update(),
                    id=article.id,
                )

                if (
                    not locked_article.is_published
                    or locked_article.is_archived
                    or locked_article.draft_type
                    != Article.DraftType.NORMAL
                ):

                    messages.warning(
                        request,
                        (
                            "This article is no longer "
                            "available for reporting."
                        ),
                    )

                    return redirect(
                        "published_articles"
                    )

                existing_report = (
                    ContentReport.objects.filter(
                        article=locked_article,
                        reported_by=request.user,
                        status__in=[
                            ContentReport.Status.OPEN,
                            ContentReport.Status.REVISION_REQUIRED,
                        ],
                    ).exists()
                )

                if existing_report:

                    messages.warning(
                        request,
                        (
                            "You already have an active "
                            "report for this article."
                        ),
                    )

                    return redirect(
                        "my_content_reports"
                    )

                ContentReport.objects.create(
                    article=locked_article,
                    reported_by=request.user,
                    description=description,
                    status=ContentReport.Status.OPEN,
                )

                notify_eics(
                    Notification.Type.CONTENT_REPORT,
                    (
                        f'{request.user.username} reported '
                        f'a content concern for '
                        f'"{locked_article.title}".'
                    ),
                    reverse(
                        "eic_content_reports"
                    ),
                    exclude_user_id=request.user.id,
                )

            messages.success(
                request,
                (
                    f'Your content report for '
                    f'"{locked_article.title}" was submitted.'
                ),
            )

            return redirect(
                "my_content_reports"
            )

    return render(
        request,
        "publications/report_article_content.html",
        {
            "article": article,
        },
    )


@publication_role_required(
    User.Role.STAFF
)
def my_content_reports(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    reports = (
        ContentReport.objects
        .filter(
            reported_by=request.user
        )
        .select_related(
            "article",
            "article__category",
            "article__author",
            "forced_edit_request",
            "forced_edit_request__draft_article",
        )
    )

    if search_query:

        reports = reports.filter(
            Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                description__icontains=search_query
            )
            | Q(
                staff_notes__icontains=search_query
            )
        )

    reports = reports.order_by(
        "-created_at"
    )

    return render(
        request,
        "publications/my_content_reports.html",
        {
            "content_reports": reports,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.STAFF
)
@require_POST
def cancel_content_report(
    request,
    report_id,
):
    with transaction.atomic():

        report = get_object_or_404(
            ContentReport.objects
            .select_for_update()
            .select_related(
                "article"
            ),
            id=report_id,
            reported_by=request.user,
        )

        if (
            report.status
            != ContentReport.Status.OPEN
        ):

            messages.warning(
                request,
                (
                    "This report can no longer "
                    "be cancelled."
                ),
            )

            return redirect(
                "my_content_reports"
            )

        report.status = (
            ContentReport.Status.CANCELLED
        )

        report.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    messages.warning(
        request,
        (
            f'Your report for '
            f'"{report.article.title}" was cancelled.'
        ),
    )

    return redirect(
        "my_content_reports"
    )


@publication_role_required(
    User.Role.EIC
)
def eic_content_reports(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    reports = (
        ContentReport.objects
        .filter(
            status__in=[
                ContentReport.Status.OPEN,
                ContentReport.Status.REVISION_REQUIRED,
            ]
        )
        .select_related(
            "article",
            "article__category",
            "article__author",
            "reported_by",
            "forced_edit_request",
            "forced_edit_request__draft_article",
        )
    )

    if search_query:

        reports = reports.filter(
            Q(
                article__title__icontains=search_query
            )
            | Q(
                article__subtitle__icontains=search_query
            )
            | Q(
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                article__author__username__icontains=search_query
            )
            | Q(
                reported_by__username__icontains=search_query
            )
            | Q(
                description__icontains=search_query
            )
            | Q(
                staff_notes__icontains=search_query
            )
        )

    reports = reports.order_by(
        "-created_at"
    )

    return render(
        request,
        "publications/eic_content_reports.html",
        {
            "content_reports": reports,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def resolve_content_report(
    request,
    report_id,
):
    staff_notes = request.POST.get(
        "staff_notes",
        "",
    ).strip()

    if not staff_notes:

        messages.error(
            request,
            (
                "Resolution notes are required when "
                "resolving a report without revision."
            ),
        )

        return redirect(
            "eic_content_reports"
        )

    with transaction.atomic():

        report = get_object_or_404(
            ContentReport.objects
            .select_for_update()
            .select_related(
                "article",
                "reported_by",
            ),
            id=report_id,
        )

        if (
            report.status
            != ContentReport.Status.OPEN
        ):

            messages.warning(
                request,
                (
                    "This report is no longer "
                    "available for resolution."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        report.status = (
            ContentReport.Status.RESOLVED
        )

        report.staff_notes = staff_notes
        report.resolved_at = timezone.now()

        report.save(
            update_fields=[
                "status",
                "staff_notes",
                "resolved_at",
                "updated_at",
            ]
        )

        notify_user(
            report.reported_by,
            Notification.Type.CONTENT_REPORT,
            (
                f'Your content report for '
                f'"{report.article.title}" was resolved '
                f'without requiring a revision.'
            ),
            reverse(
                "my_content_reports"
            ),
        )

    messages.success(
        request,
        (
            f'The report for '
            f'"{report.article.title}" was resolved.'
        ),
    )

    return redirect(
        "eic_content_reports"
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def require_revision_from_report(
    request,
    report_id,
):
    staff_notes = request.POST.get(
        "staff_notes",
        "",
    ).strip()

    if not staff_notes:

        messages.error(
            request,
            "Revision instructions are required.",
        )

        return redirect(
            "eic_content_reports"
        )

    with transaction.atomic():

        report = get_object_or_404(
            ContentReport.objects
            .select_for_update()
            .select_related(
                "article",
                "article__author",
                "reported_by",
            ),
            id=report_id,
        )

        if (
            report.status
            != ContentReport.Status.OPEN
        ):

            messages.warning(
                request,
                (
                    "This report is no longer available "
                    "for a revision requirement."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        original_article = (
            Article.objects
            .select_for_update()
            .select_related(
                "author",
                "category",
            )
            .prefetch_related(
                "tags",
                "contributors",
                "contributors__user",
                "attachments",
                "video_attachments",
            )
            .get(
                id=report.article_id
            )
        )

        if not original_article.is_published:

            messages.warning(
                request,
                (
                    "This article is no longer "
                    "published."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        if original_article.is_archived:

            messages.warning(
                request,
                "This article is already archived.",
            )

            return redirect(
                "eic_content_reports"
            )

        if (
            original_article.draft_type
            != Article.DraftType.NORMAL
        ):

            messages.warning(
                request,
                (
                    "Only normal published articles "
                    "can be forced into revision."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        if original_article.author.role not in [
            User.Role.EDITOR,
            User.Role.EIC,
        ]:

            messages.warning(
                request,
                (
                    "Corrective revisions can only be "
                    "assigned to articles authored by an "
                    "Editor or the Editor in Chief."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        if (
            original_article.author.role
            == User.Role.EIC
        ):

            report.status = (
                ContentReport.Status.REVISION_REQUIRED
            )

            report.staff_notes = staff_notes

            report.forced_edit_request = None

            report.save(
                update_fields=[
                    "status",
                    "staff_notes",
                    "forced_edit_request",
                    "updated_at",
                ]
            )

            notify_user(
                original_article.author,
                Notification.Type.REVISION,
                (
                    f'A corrective revision is required for '
                    f'your article "{original_article.title}" '
                    f'because of a Staff content report.'
                ),
                reverse(
                    "edit_published_article",
                    args=[
                        original_article.id
                    ],
                ),
            )

            notify_user(
                report.reported_by,
                Notification.Type.CONTENT_REPORT,
                (
                    f'The EIC reviewed your report for '
                    f'"{original_article.title}" and marked '
                    f'the article for corrective revision.'
                ),
                reverse(
                    "my_content_reports"
                ),
            )

            messages.success(
                request,
                (
                    f'"{original_article.title}" was marked '
                    f'for corrective revision. Because the '
                    f'article belongs to the EIC, the revision '
                    f'will be completed through direct editing.'
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        existing_edit_request = (
            EditRequest.objects.filter(
                article=original_article,
                status__in=[
                    EditRequest.Status.PENDING,
                    EditRequest.Status.APPROVED,
                ],
            ).exists()
        )

        if existing_edit_request:

            messages.warning(
                request,
                (
                    "An active edit request already "
                    "exists for this article."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        existing_deletion_request = (
            DeletionRequest.objects.filter(
                article=original_article,
                status=DeletionRequest.Status.PENDING,
            ).exists()
        )

        if existing_deletion_request:

            messages.warning(
                request,
                (
                    "A deletion request is currently "
                    "pending for this article."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        existing_draft = (
            Article.objects.filter(
                source_article=original_article,
                draft_type=(
                    Article.DraftType.EDIT_REQUEST
                ),
                is_published=False,
                is_archived=False,
            ).exists()
        )

        if existing_draft:

            messages.warning(
                request,
                (
                    "An active revision draft already "
                    "exists for this article."
                ),
            )

            return redirect(
                "eic_content_reports"
            )

        forced_edit_request = (
            EditRequest.objects.create(
                article=original_article,
                requested_by=original_article.author,
                reason=(
                    "Revision required by the "
                    "Editor in Chief because of "
                    f"Staff Content Report #{report.id}."
                ),
                status=EditRequest.Status.APPROVED,
                reviewer_notes=staff_notes,
                reviewed_at=timezone.now(),
            )
        )

        edit_draft_slug = (
            generate_unique_article_slug(
                original_article.title,
                suffix=(
                    f"report-revision-{report.id}"
                ),
            )
        )

        edit_draft = Article.objects.create(
            title=original_article.title,
            subtitle=original_article.subtitle,
            excerpt=original_article.excerpt,
            slug=edit_draft_slug,
            category=original_article.category,
            attachment_mode=original_article.attachment_mode,
            author=original_article.author,
            content=original_article.content,
            featured_image=(
                original_article.featured_image
            ),
            featured_image_caption=(
                original_article
                .featured_image_caption
            ),
            featured_image_credit=(
                original_article
                .featured_image_credit
            ),
            version_number=(
                original_article.version_number
                + 1
            ),
            draft_type=(
                Article.DraftType.EDIT_REQUEST
            ),
            source_article=original_article,
            is_published=False,
            is_archived=False,
        )

        edit_draft.tags.set(
            original_article.tags.all()
        )

        copy_article_contributors(
            original_article,
            edit_draft,
        )

        copy_article_attachments(
            original_article,
            edit_draft,
        )

        copy_article_video_attachments(
            original_article,
            edit_draft,
        )

        forced_edit_request.draft_article = (
            edit_draft
        )

        forced_edit_request.save(
            update_fields=[
                "draft_article",
            ]
        )

        report.status = (
            ContentReport.Status.REVISION_REQUIRED
        )

        report.staff_notes = staff_notes

        report.forced_edit_request = (
            forced_edit_request
        )

        report.save(
            update_fields=[
                "status",
                "staff_notes",
                "forced_edit_request",
                "updated_at",
            ]
        )

        notify_user(
            original_article.author,
            Notification.Type.REVISION,
            (
                f'The EIC required a corrective revision '
                f'for "{original_article.title}" because '
                f'of a Staff content report.'
            ),
            reverse(
                "my_drafts"
            ),
        )

        notify_user(
            report.reported_by,
            Notification.Type.CONTENT_REPORT,
            (
                f'The EIC reviewed your report for '
                f'"{original_article.title}" and required '
                f'a corrective revision.'
            ),
            reverse(
                "my_content_reports"
            ),
        )

    messages.success(
        request,
        (
            f'A corrective revision for '
            f'"{original_article.title}" was assigned '
            f'to {original_article.author.username}.'
        ),
    )

    return redirect(
        "eic_content_reports"
    )


# ==========================================================
# ARCHIVE MANAGEMENT
# ==========================================================


@publication_role_required(
    User.Role.EIC
)
def archived_articles(request):
    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    articles = (
        Article.objects
        .filter(
            is_archived=True,
            draft_type=Article.DraftType.NORMAL,
        )
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "attachments",
            "video_attachments",
            "tags",
            "contributors",
            "contributors__user",
        )
    )

    if search_query:

        articles = articles.filter(
            Q(
                title__icontains=search_query
            )
            | Q(
                subtitle__icontains=search_query
            )
            | Q(
                excerpt__icontains=search_query
            )
            | Q(
                content__icontains=search_query
            )
            | Q(
                category__name__icontains=search_query
            )
            | Q(
                author__username__icontains=search_query
            )
            | Q(
                contributors__user__username__icontains=search_query
            )
            | Q(
                contributors__role__icontains=search_query
            )
            | Q(
                tags__name__icontains=search_query
            )
        )

    articles = (
        articles
        .order_by(
            "-archived_at",
            "-updated_at",
        )
        .distinct()
    )

    return render(
        request,
        "publications/archive.html",
        {
            "articles": articles,
            "search_query": search_query,
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def restore_archived_article(
    request,
    article_id,
):
    with transaction.atomic():

        article = get_object_or_404(
            Article.objects
            .select_for_update()
            .select_related(
                "author",
                "category",
            ),
            id=article_id,
            draft_type=Article.DraftType.NORMAL,
        )

        if not article.is_archived:

            messages.warning(
                request,
                (
                    "This article is no longer "
                    "archived."
                ),
            )

            return redirect(
                "archived_articles"
            )

        active_edit_request = (
            EditRequest.objects.filter(
                article=article,
                status__in=[
                    EditRequest.Status.PENDING,
                    EditRequest.Status.APPROVED,
                ],
            ).exists()
        )

        if active_edit_request:

            messages.warning(
                request,
                (
                    "This archived article cannot be restored "
                    "while an edit request is active."
                ),
            )

            return redirect(
                "archived_articles"
            )

        article.is_archived = False
        article.is_published = True
        article.archived_at = None

        if article.published_at is None:

            article.published_at = (
                timezone.now()
            )

        article.save(
            update_fields=[
                "is_archived",
                "is_published",
                "archived_at",
                "published_at",
                "updated_at",
            ]
        )

        if (
            article.author.role
            == User.Role.EDITOR
        ):

            notify_user(
                article.author,
                Notification.Type.GENERAL,
                (
                    f'The archived article '
                    f'"{article.title}" was restored '
                    f'by the Editor in Chief.'
                ),
                reverse(
                    "published_articles"
                ),
            )

    messages.success(
        request,
        (
            f'"{article.title}" was restored '
            f'and published again.'
        ),
    )

    return redirect(
        "archived_articles"
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def permanently_delete_archived_article(
    request,
    article_id,
):
    """
    Permanently purge an archived NORMAL article.

    Database relations tied to the article are removed through the
    models' existing on_delete behavior. Media paths owned by the
    archived article, its historical submission snapshots, version
    snapshots, and its edit-request drafts are collected before the
    database purge and then removed from storage.
    """

    media_names = set()

    with transaction.atomic():

        article = get_object_or_404(
            Article.objects
            .select_for_update()
            .select_related(
                "author",
                "category",
            )
            .prefetch_related(
                "attachments",
                "video_attachments",
                "submissions",
                "submissions__snapshot_attachments",
                "submissions__snapshot_video_attachments",
            ),
            id=article_id,
            is_archived=True,
            draft_type=Article.DraftType.NORMAL,
        )

        active_edit_request_exists = (
            EditRequest.objects.filter(
                article=article,
                status__in=[
                    EditRequest.Status.PENDING,
                    EditRequest.Status.APPROVED,
                ],
            ).exists()
        )

        active_content_report_exists = (
            ContentReport.objects.filter(
                article=article,
                status__in=[
                    ContentReport.Status.OPEN,
                    ContentReport.Status.REVISION_REQUIRED,
                ],
            ).exists()
        )

        if (
            active_edit_request_exists
            or active_content_report_exists
        ):

            messages.warning(
                request,
                (
                    "This archived article cannot be permanently "
                    "deleted while an editorial workflow is still active."
                ),
            )

            return redirect(
                "archived_articles"
            )

        article_title = article.title

        # --------------------------------------------------
        # Current article media
        # --------------------------------------------------

        if article.featured_image:
            media_names.add(
                article.featured_image.name
            )

        for attachment in article.attachments.all():

            if attachment.image:
                media_names.add(
                    attachment.image.name
                )

        for attachment in article.video_attachments.all():

            if attachment.video:
                media_names.add(
                    attachment.video.name
                )

        # --------------------------------------------------
        # Submission snapshot media
        # --------------------------------------------------

        for submission in article.submissions.all():

            if submission.snapshot_featured_image:
                media_names.add(
                    submission.snapshot_featured_image
                )

            for attachment in (
                submission.snapshot_attachments.all()
            ):

                if attachment.image:
                    media_names.add(
                        attachment.image
                    )

            for attachment in (
                submission.snapshot_video_attachments.all()
            ):

                if attachment.video:
                    media_names.add(
                        attachment.video
                    )

        # --------------------------------------------------
        # Immutable article-version snapshot media
        # --------------------------------------------------

        media_names.update(
            name
            for name in (
                ArticleVersion.objects
                .filter(article=article)
                .exclude(featured_image="")
                .values_list(
                    "featured_image",
                    flat=True,
                )
            )
            if name
        )

        media_names.update(
            name
            for name in (
                ArticleVersionImageAttachment.objects
                .filter(
                    article_version__article=article
                )
                .exclude(image="")
                .values_list(
                    "image",
                    flat=True,
                )
            )
            if name
        )

        media_names.update(
            name
            for name in (
                ArticleVersionVideoAttachment.objects
                .filter(
                    article_version__article=article
                )
                .exclude(video="")
                .values_list(
                    "video",
                    flat=True,
                )
            )
            if name
        )

        # --------------------------------------------------
        # Historical edit-request drafts sourced from article
        # --------------------------------------------------

        related_edit_drafts = list(
            Article.objects
            .filter(
                source_article=article,
                draft_type=Article.DraftType.EDIT_REQUEST,
            )
            .prefetch_related(
                "attachments",
                "video_attachments",
            )
        )

        for draft in related_edit_drafts:

            if draft.featured_image:
                media_names.add(
                    draft.featured_image.name
                )

            for attachment in draft.attachments.all():

                if attachment.image:
                    media_names.add(
                        attachment.image.name
                    )

            for attachment in draft.video_attachments.all():

                if attachment.video:
                    media_names.add(
                        attachment.video.name
                    )

        # Delete edit drafts first because source_article uses SET_NULL.
        for draft in related_edit_drafts:
            draft.delete()

        # Existing CASCADE relations remove submissions, reports,
        # requests, contributors, attachments, versions, etc.
        article.delete()

    # Storage deletion happens only after the database transaction
    # successfully commits.
    storage_cleanup_failed = False

    for media_name in media_names:

        if not media_name:
            continue

        try:

            if default_storage.exists(
                media_name
            ):
                default_storage.delete(
                    media_name
                )

        except Exception:
            storage_cleanup_failed = True

    if storage_cleanup_failed:

        messages.warning(
            request,
            (
                f'"{article_title}" was permanently deleted from '
                "the database, but one or more associated media "
                "files could not be removed from storage."
            ),
        )

    else:

        messages.success(
            request,
            (
                f'"{article_title}" was permanently deleted.'
            ),
        )

    return redirect(
        "archived_articles"
    )



# ==========================================================
# PUBLIC CONTENT FORM LIMIT HELPERS
# ==========================================================


def validate_management_text_limit(value, label, max_length):
    if len(value or "") > max_length:
        raise ValidationError(
            f"{label} cannot exceed {max_length} characters."
        )


def digital_publication_management_context():
    publications = (
        DigitalPublication.objects
        .select_related("uploaded_by")
        .all()
    )
    return {
        "digital_publications": publications,
        "status_choices": DigitalPublication.Status.choices,
    }


def school_advertisement_management_context():
    advertisements = (
        SchoolAdvertisement.objects
        .select_related("created_by", "updated_by")
        .all()
    )
    return {
        "advertisements": advertisements,
        "active_advertisements": advertisements.filter(is_active=True),
    }


# ==========================================================
# DIGITAL PUBLICATION MANAGEMENT
# EIC ONLY
# ==========================================================


def get_digital_publication_form_data(
    request,
):
    title = request.POST.get(
        "title",
        "",
    ).strip()

    volume = request.POST.get(
        "volume",
        "",
    ).strip()

    issue_number = request.POST.get(
        "issue_number",
        "",
    ).strip()

    publication_date = request.POST.get(
        "publication_date",
        "",
    ).strip()

    description = request.POST.get(
        "description",
        "",
    ).strip()

    status = request.POST.get(
        "status",
        DigitalPublication.Status.DRAFT,
    ).strip()

    display_order_raw = request.POST.get(
        "display_order",
        "0",
    ).strip()

    validate_management_text_limit(title, "Publication title", 180)
    validate_management_text_limit(volume, "Volume", 50)
    validate_management_text_limit(issue_number, "Issue number", 50)
    validate_management_text_limit(description, "Description", 1500)

    if not title:
        raise ValidationError(
            "Please provide a publication title."
        )

    if not publication_date:
        raise ValidationError(
            "Please provide a publication date."
        )

    valid_statuses = {
        choice_value
        for choice_value, choice_label
        in DigitalPublication.Status.choices
    }

    if status not in valid_statuses:
        raise ValidationError(
            "An invalid publication status was selected."
        )

    try:
        display_order = int(
            display_order_raw or 0
        )
    except ValueError as error:
        raise ValidationError(
            "Display order must be a whole number."
        ) from error

    if display_order < 0:
        raise ValidationError(
            "Display order cannot be negative."
        )

    if display_order > 9999:
        raise ValidationError(
            "Display order cannot exceed 9999."
        )

    return {
        "title": title,
        "volume": volume,
        "issue_number": issue_number,
        "publication_date": publication_date,
        "description": description,
        "status": status,
        "display_order": display_order,
    }


@publication_role_required(
    User.Role.EIC
)
def digital_publication_management(
    request,
):
    return render(
        request,
        "publications/digital_publication_management.html",
        digital_publication_management_context(),
    )

@publication_role_required(
    User.Role.EIC
)
@require_POST
def create_digital_publication(
    request,
):
    try:
        form_data = (
            get_digital_publication_form_data(
                request
            )
        )

        pdf_file = request.FILES.get(
            "pdf_file"
        )

        cover_image = request.FILES.get(
            "cover_image"
        )

        if not pdf_file:
            raise ValidationError(
                "Please upload a publication PDF."
            )

        metadata = (
            inspect_digital_publication_pdf(
                pdf_file
            )
        )

        publication = (
            DigitalPublication(
                uploaded_by=request.user,
                pdf_file=pdf_file,
                cover_image=cover_image,
                page_count=(
                    metadata["page_count"]
                ),
                file_size=(
                    metadata["file_size"]
                ),
                **form_data,
            )
        )

        if (
            publication.status
            == DigitalPublication.Status.PUBLISHED
        ):
            publication.published_at = (
                timezone.now()
            )

        publication.full_clean()
        publication.save()

    except ValidationError as error:
        messages.error(
            request,
            get_validation_error_message(
                error
            ),
        )

        return render(
            request,
            "publications/digital_publication_management.html",
            digital_publication_management_context(),
        )


    messages.success(
        request,
        (
            f'"{publication.title}" '
            "was added successfully."
        ),
    )

    return redirect(
        "digital_publication_management"
    )


@publication_role_required(
    User.Role.EIC
)
def edit_digital_publication(
    request,
    publication_id,
):
    publication = get_object_or_404(
        DigitalPublication,
        id=publication_id,
    )

    if request.method == "POST":
        old_pdf_name = (
            publication.pdf_file.name
            if publication.pdf_file
            else ""
        )

        old_cover_name = (
            publication.cover_image.name
            if publication.cover_image
            else ""
        )

        try:
            form_data = (
                get_digital_publication_form_data(
                    request
                )
            )

            replacement_pdf = (
                request.FILES.get(
                    "pdf_file"
                )
            )

            replacement_cover = (
                request.FILES.get(
                    "cover_image"
                )
            )

            remove_cover = (
                request.POST.get(
                    "remove_cover"
                )
                == "1"
            )

            publication.title = (
                form_data["title"]
            )
            publication.volume = (
                form_data["volume"]
            )
            publication.issue_number = (
                form_data["issue_number"]
            )
            publication.publication_date = (
                form_data[
                    "publication_date"
                ]
            )
            publication.description = (
                form_data["description"]
            )
            publication.status = (
                form_data["status"]
            )
            publication.display_order = (
                form_data["display_order"]
            )

            if replacement_pdf:
                metadata = (
                    inspect_digital_publication_pdf(
                        replacement_pdf
                    )
                )

                publication.pdf_file = (
                    replacement_pdf
                )

                publication.page_count = (
                    metadata["page_count"]
                )

                publication.file_size = (
                    metadata["file_size"]
                )

            if replacement_cover:
                publication.cover_image = (
                    replacement_cover
                )
            elif remove_cover:
                publication.cover_image = None

            if (
                publication.status
                == DigitalPublication.Status.PUBLISHED
            ):
                if not publication.published_at:
                    publication.published_at = (
                        timezone.now()
                    )
            else:
                publication.published_at = None

            publication.full_clean()
            publication.save()

        except ValidationError as error:
            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                (
                    "publications/"
                    "edit_digital_publication.html"
                ),
                {
                    "publication": publication,
                    "status_choices": (
                        DigitalPublication
                        .Status
                        .choices
                    ),
                },
            )

        if (
            replacement_pdf
            and old_pdf_name
            and old_pdf_name
            != publication.pdf_file.name
        ):
            delete_storage_file_safely(
                old_pdf_name
            )

        if (
            (
                replacement_cover
                or remove_cover
            )
            and old_cover_name
            and (
                not publication.cover_image
                or old_cover_name
                != publication.cover_image.name
            )
        ):
            delete_storage_file_safely(
                old_cover_name
            )

        messages.success(
            request,
            (
                f'"{publication.title}" '
                "was updated successfully."
            ),
        )

        return redirect(
            "digital_publication_management"
        )

    return render(
        request,
        (
            "publications/"
            "edit_digital_publication.html"
        ),
        {
            "publication": publication,
            "status_choices": (
                DigitalPublication.Status.choices
            ),
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def set_digital_publication_status(
    request,
    publication_id,
):
    publication = get_object_or_404(
        DigitalPublication,
        id=publication_id,
    )

    requested_status = request.POST.get(
        "status",
        "",
    )

    valid_statuses = {
        choice_value
        for choice_value, choice_label
        in DigitalPublication.Status.choices
    }

    if requested_status not in valid_statuses:
        messages.error(
            request,
            "Invalid publication status.",
        )

        return redirect(
            "digital_publication_management"
        )

    publication.status = (
        requested_status
    )

    if (
        requested_status
        == DigitalPublication.Status.PUBLISHED
    ):
        if not publication.published_at:
            publication.published_at = (
                timezone.now()
            )
    else:
        publication.published_at = None

    publication.save(
        update_fields=[
            "status",
            "published_at",
            "updated_at",
        ]
    )

    messages.success(
        request,
        (
            f'"{publication.title}" is now '
            f'{publication.get_status_display()}.'
        ),
    )

    return redirect(
        "digital_publication_management"
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def delete_digital_publication(
    request,
    publication_id,
):
    publication = get_object_or_404(
        DigitalPublication,
        id=publication_id,
    )

    title = publication.title

    pdf_name = (
        publication.pdf_file.name
        if publication.pdf_file
        else ""
    )

    cover_name = (
        publication.cover_image.name
        if publication.cover_image
        else ""
    )

    publication.delete()

    for file_name in {
        pdf_name,
        cover_name,
    }:
        if file_name:
            delete_storage_file_safely(
                file_name
            )

    messages.success(
        request,
        (
            f'"{title}" was permanently deleted '
            "from Digital Publications."
        ),
    )

    return redirect(
        "digital_publication_management"
    )


# ==========================================================
# SCHOOL ADVERTISEMENT MANAGEMENT
# EIC ONLY
# ==========================================================


def get_school_advertisement_form_data(
    request,
):
    title = request.POST.get(
        "title",
        "",
    ).strip()

    summary = request.POST.get(
        "summary",
        "",
    ).strip()

    details = request.POST.get(
        "details",
        "",
    ).strip()

    display_order_raw = request.POST.get(
        "display_order",
        "0",
    ).strip()

    is_active = (
        request.POST.get(
            "is_active",
            "",
        )
        == "1"
    )

    validate_management_text_limit(title, "Advertisement title", 180)
    validate_management_text_limit(summary, "Short summary", 320)
    validate_management_text_limit(details, "Full details", 3000)

    if not title:
        raise ValidationError(
            "Please provide an advertisement title."
        )

    if not summary:
        raise ValidationError(
            "Please provide a short advertisement summary."
        )

    if not details:
        raise ValidationError(
            "Please provide the full school update details."
        )

    try:
        display_order = int(
            display_order_raw or 0
        )
    except ValueError as error:
        raise ValidationError(
            "Display order must be a whole number."
        ) from error

    if display_order < 0:
        raise ValidationError(
            "Display order cannot be negative."
        )

    if display_order > 9999:
        raise ValidationError(
            "Display order cannot exceed 9999."
        )

    return {
        "title": title,
        "summary": summary,
        "details": details,
        "display_order": display_order,
        "is_active": is_active,
    }


@publication_role_required(
    User.Role.EIC
)
def school_advertisement_management(
    request,
):
    return render(
        request,
        "publications/school_advertisement_management.html",
        school_advertisement_management_context(),
    )

@publication_role_required(
    User.Role.EIC
)
@require_POST
def create_school_advertisement(
    request,
):
    try:
        form_data = (
            get_school_advertisement_form_data(
                request
            )
        )

        image = request.FILES.get(
            "image"
        )

        if not image:
            raise ValidationError(
                "Please upload an advertisement image."
            )

        validate_article_image(
            image
        )

        advertisement = SchoolAdvertisement(
            created_by=request.user,
            updated_by=request.user,
            image=image,
            **form_data,
        )

        advertisement.full_clean()
        advertisement.save()

    except ValidationError as error:
        messages.error(
            request,
            get_validation_error_message(
                error
            ),
        )

        return render(
            request,
            "publications/school_advertisement_management.html",
            school_advertisement_management_context(),
        )

    messages.success(
        request,
        (
            f'"{advertisement.title}" '
            "was added to School Updates."
        ),
    )

    return redirect(
        "school_advertisement_management"
    )


@publication_role_required(
    User.Role.EIC
)
def edit_school_advertisement(
    request,
    advertisement_id,
):
    advertisement = get_object_or_404(
        SchoolAdvertisement,
        id=advertisement_id,
    )

    if request.method == "POST":
        old_image_name = (
            advertisement.image.name
            if advertisement.image
            else ""
        )

        replacement_image = None

        try:
            form_data = (
                get_school_advertisement_form_data(
                    request
                )
            )

            replacement_image = (
                request.FILES.get(
                    "image"
                )
            )

            if replacement_image:
                validate_article_image(
                    replacement_image
                )

            advertisement.title = (
                form_data["title"]
            )
            advertisement.summary = (
                form_data["summary"]
            )
            advertisement.details = (
                form_data["details"]
            )
            advertisement.display_order = (
                form_data["display_order"]
            )
            advertisement.is_active = (
                form_data["is_active"]
            )
            advertisement.updated_by = (
                request.user
            )

            if replacement_image:
                advertisement.image = (
                    replacement_image
                )

            advertisement.full_clean()
            advertisement.save()

        except ValidationError as error:
            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                (
                    "publications/"
                    "edit_school_advertisement.html"
                ),
                {
                    "advertisement": (
                        advertisement
                    ),
                },
            )

        if (
            replacement_image
            and old_image_name
            and old_image_name
            != advertisement.image.name
        ):
            delete_storage_file_safely(
                old_image_name
            )

        messages.success(
            request,
            (
                f'"{advertisement.title}" '
                "was updated successfully."
            ),
        )

        return redirect(
            "school_advertisement_management"
        )

    return render(
        request,
        (
            "publications/"
            "edit_school_advertisement.html"
        ),
        {
            "advertisement": advertisement,
        },
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def set_school_advertisement_status(
    request,
    advertisement_id,
):
    advertisement = get_object_or_404(
        SchoolAdvertisement,
        id=advertisement_id,
    )

    requested_active = (
        request.POST.get(
            "is_active",
            "0",
        )
        == "1"
    )

    advertisement.is_active = (
        requested_active
    )
    advertisement.updated_by = (
        request.user
    )
    advertisement.save(
        update_fields=[
            "is_active",
            "updated_by",
            "updated_at",
        ]
    )

    messages.success(
        request,
        (
            f'"{advertisement.title}" is now '
            + (
                "visible on the public site."
                if requested_active
                else "hidden from the public site."
            )
        ),
    )

    return redirect(
        "school_advertisement_management"
    )


@publication_role_required(
    User.Role.EIC
)
@require_POST
def delete_school_advertisement(
    request,
    advertisement_id,
):
    advertisement = get_object_or_404(
        SchoolAdvertisement,
        id=advertisement_id,
    )

    title = advertisement.title

    image_name = (
        advertisement.image.name
        if advertisement.image
        else ""
    )

    advertisement.delete()

    if image_name:
        delete_storage_file_safely(
            image_name
        )

    messages.success(
        request,
        (
            f'"{title}" was permanently deleted '
            "from School Updates."
        ),
    )

    return redirect(
        "school_advertisement_management"
    )



# ==========================================================
# PEOPLE & TEAMS MANAGEMENT
# ==========================================================

PEOPLE_SECTIONS = {
    "developers": {
        "section": PeopleProfile.Section.DEVELOPERS,
        "title": "The Developers",
        "role": User.Role.ADMIN,
    },
    "capstone-committee": {
        "section": PeopleProfile.Section.CAPSTONE_COMMITTEE,
        "title": "Capstone Committee",
        "role": User.Role.ADMIN,
    },
    "ics-faculty": {
        "section": PeopleProfile.Section.ICS_FACULTY,
        "title": "ICS Faculty",
        "role": User.Role.ADMIN,
    },
    "equalizer-team": {
        "section": PeopleProfile.Section.EQUALIZER_TEAM,
        "title": "The Equalizer Team",
        "role": User.Role.EIC,
    },
}


def get_people_section(section_slug):
    return PEOPLE_SECTIONS.get(section_slug)


def can_manage_people_section(user, config):
    return bool(config and user.role == config["role"])


def read_people_form(request):
    name = request.POST.get("name", "").strip()
    role_title = request.POST.get("role_title", "").strip()
    courses_handled = request.POST.get("courses_handled", "").strip()
    school_position = request.POST.get("school_position", "").strip()
    institute_department = request.POST.get("institute_department", "").strip()
    achievements = request.POST.get("achievements", "").strip()
    additional_information = request.POST.get("additional_information", "").strip()

    validate_management_text_limit(name, "Name", 40)
    validate_management_text_limit(role_title, "Primary role / title", 40)
    validate_management_text_limit(courses_handled, "Courses handled", 180)
    validate_management_text_limit(school_position, "School position", 60)
    validate_management_text_limit(institute_department, "Institute / department", 60)
    validate_management_text_limit(achievements, "Achievements / contributions", 300)
    validate_management_text_limit(additional_information, "Additional information", 300)

    if not name:
        raise ValidationError("Please provide the person's name.")

    try:
        display_order = int(request.POST.get("display_order", "0").strip() or 0)
    except ValueError as error:
        raise ValidationError("Display order must be a whole number.") from error

    if display_order < 0:
        raise ValidationError("Display order cannot be negative.")
    if display_order > 9999:
        raise ValidationError("Display order cannot exceed 9999.")

    return {
        "name": name,
        "role_title": role_title,
        "courses_handled": courses_handled,
        "school_position": school_position,
        "institute_department": institute_department,
        "achievements": achievements,
        "additional_information": additional_information,
        "display_order": display_order,
        "is_active": request.POST.get("is_active", "") == "1",
    }

@publication_role_required(User.Role.ADMIN, User.Role.EIC)
def people_management(request):
    sections = []

    for slug, config in PEOPLE_SECTIONS.items():
        if not can_manage_people_section(request.user, config):
            continue

        queryset = PeopleProfile.objects.filter(
            section=config["section"]
        )
        sections.append({
            "slug": slug,
            "title": config["title"],
            "count": queryset.count(),
            "active_count": queryset.filter(is_active=True).count(),
        })

    return render(
        request,
        "publications/people_management.html",
        {"sections": sections},
    )


@publication_role_required(User.Role.ADMIN, User.Role.EIC)
def people_group_management(request, section_slug):
    config = get_people_section(section_slug)

    if not can_manage_people_section(request.user, config):
        return HttpResponseForbidden(
            "You do not have permission to manage this section."
        )

    profiles = (
        PeopleProfile.objects
        .filter(section=config["section"])
        .order_by("display_order", "name")
    )

    return render(
        request,
        "publications/people_group_management.html",
        {
            "section_slug": section_slug,
            "section_title": config["title"],
            "profiles": profiles,
        },
    )


@publication_role_required(User.Role.ADMIN, User.Role.EIC)
@require_POST
def create_people_profile(request, section_slug):
    config = get_people_section(section_slug)

    if not can_manage_people_section(request.user, config):
        return HttpResponseForbidden(
            "You do not have permission to create profiles here."
        )

    try:
        data = read_people_form(request)
        image = request.FILES.get("image")

        if not image:
            raise ValidationError("Please upload a profile image.")

        validate_article_image(image)

        profile = PeopleProfile(
            section=config["section"],
            image=image,
            created_by=request.user,
            updated_by=request.user,
            **data,
        )
        profile.full_clean()
        profile.save()

        messages.success(
            request,
            f'"{profile.name}" was added to {config["title"]}.',
        )

    except ValidationError as error:
        messages.error(
            request,
            get_validation_error_message(error),
        )
        profiles = (
            PeopleProfile.objects
            .filter(section=config["section"])
            .order_by("display_order", "name")
        )
        return render(
            request,
            "publications/people_group_management.html",
            {
                "section_slug": section_slug,
                "section_title": config["title"],
                "profiles": profiles,
            },
        )

    return redirect(
        "people_group_management",
        section_slug=section_slug,
    )


@publication_role_required(User.Role.ADMIN, User.Role.EIC)
def edit_people_profile(request, section_slug, profile_id):
    config = get_people_section(section_slug)

    if not can_manage_people_section(request.user, config):
        return HttpResponseForbidden(
            "You do not have permission to edit this section."
        )

    profile = get_object_or_404(
        PeopleProfile,
        id=profile_id,
        section=config["section"],
    )

    if request.method == "POST":
        old_image_name = profile.image.name if profile.image else ""
        replacement_image = request.FILES.get("image")

        try:
            data = read_people_form(request)

            if replacement_image:
                validate_article_image(replacement_image)

            for field, value in data.items():
                setattr(profile, field, value)

            profile.updated_by = request.user

            if replacement_image:
                profile.image = replacement_image

            profile.full_clean()
            profile.save()

        except ValidationError as error:
            messages.error(
                request,
                get_validation_error_message(error),
            )
        else:
            if (
                replacement_image
                and old_image_name
                and old_image_name != profile.image.name
            ):
                delete_storage_file_safely(
                    old_image_name
                )

            messages.success(
                request,
                f'"{profile.name}" was updated successfully.',
            )

            return redirect(
                "people_group_management",
                section_slug=section_slug,
            )

    return render(
        request,
        "publications/edit_people_profile.html",
        {
            "profile": profile,
            "section_slug": section_slug,
            "section_title": config["title"],
        },
    )


@publication_role_required(User.Role.ADMIN, User.Role.EIC)
@require_POST
def set_people_profile_status(request, section_slug, profile_id):
    config = get_people_section(section_slug)

    if not can_manage_people_section(request.user, config):
        return HttpResponseForbidden(
            "You do not have permission to update this profile."
        )

    profile = get_object_or_404(
        PeopleProfile,
        id=profile_id,
        section=config["section"],
    )

    profile.is_active = request.POST.get("is_active", "0") == "1"
    profile.updated_by = request.user
    profile.save(
        update_fields=["is_active", "updated_by", "updated_at"]
    )

    return redirect(
        "people_group_management",
        section_slug=section_slug,
    )


@publication_role_required(User.Role.ADMIN, User.Role.EIC)
@require_POST
def delete_people_profile(request, section_slug, profile_id):
    config = get_people_section(section_slug)

    if not can_manage_people_section(request.user, config):
        return HttpResponseForbidden(
            "You do not have permission to delete this profile."
        )

    profile = get_object_or_404(
        PeopleProfile,
        id=profile_id,
        section=config["section"],
    )

    image_name = profile.image.name if profile.image else ""
    name = profile.name
    profile.delete()

    if image_name:
        delete_storage_file_safely(
            image_name
        )

    messages.success(
        request,
        f'"{name}" was permanently deleted.',
    )

    return redirect(
        "people_group_management",
        section_slug=section_slug,
    )


# ==========================================================
# ABOUT US PAGE MANAGEMENT
# EIC ONLY
# ==========================================================


@publication_role_required(
    User.Role.EIC
)
def about_us_management(
    request,
):
    about_page = (
        AboutUsPage.objects
        .select_related(
            "updated_by",
        )
        .first()
    )

    if request.method == "POST":
        title = request.POST.get(
            "title",
            "",
        ).strip()

        subtitle = request.POST.get(
            "subtitle",
            "",
        ).strip()

        overview = request.POST.get(
            "overview",
            "",
        ).strip()

        history = request.POST.get(
            "history",
            "",
        ).strip()

        mission = request.POST.get(
            "mission",
            "",
        ).strip()

        vision = request.POST.get(
            "vision",
            "",
        ).strip()

        is_published = (
            request.POST.get(
                "is_published",
                "",
            )
            == "1"
        )

        replacement_image = (
            request.FILES.get(
                "hero_image"
            )
        )

        old_image_name = (
            about_page.hero_image.name
            if (
                about_page
                and about_page.hero_image
            )
            else ""
        )

        try:
            validate_management_text_limit(title, "Page title", 180)
            validate_management_text_limit(subtitle, "Subtitle", 320)
            validate_management_text_limit(overview, "About overview", 5000)
            validate_management_text_limit(history, "History", 7000)
            validate_management_text_limit(mission, "Mission", 2500)
            validate_management_text_limit(vision, "Vision", 2500)

            if not title:
                raise ValidationError(
                    "Please provide an About Us page title."
                )

            if not overview:
                raise ValidationError(
                    "Please provide information about The Equalizer."
                )

            if not history:
                raise ValidationError(
                    "Please provide the publication history."
                )

            if replacement_image:
                validate_article_image(
                    replacement_image
                )

            if about_page is None:
                about_page = AboutUsPage()

            about_page.title = title
            about_page.subtitle = subtitle
            about_page.overview = overview
            about_page.history = history
            about_page.mission = mission
            about_page.vision = vision
            about_page.is_published = (
                is_published
            )
            about_page.updated_by = (
                request.user
            )

            if replacement_image:
                about_page.hero_image = (
                    replacement_image
                )

            about_page.full_clean()
            about_page.save()

        except ValidationError as error:
            messages.error(
                request,
                get_validation_error_message(
                    error
                ),
            )

            return render(
                request,
                (
                    "publications/"
                    "about_us_management.html"
                ),
                {
                    "about_page": about_page,
                },
            )

        if (
            replacement_image
            and old_image_name
            and old_image_name
            != about_page.hero_image.name
        ):
            delete_storage_file_safely(
                old_image_name
            )

        messages.success(
            request,
            (
                "The public About Us page "
                "was updated successfully."
            ),
        )

        return redirect(
            "about_us_management"
        )

    return render(
        request,
        (
            "publications/"
            "about_us_management.html"
        ),
        {
            "about_page": about_page,
        },
    )

