from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from notifications.models import Notification

from .models import (
    Article,
    ArticleAttachment,
    Category,
    ContentReport,
    DeletionRequest,
    EditRequest,
    Submission,
    Tag,
)


User = get_user_model()


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
# ARTICLE CREATION
# ==========================================================


@publication_role_required(
    User.Role.EDITOR,
    User.Role.EIC,
)
def create_article(request):

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":

        title = request.POST.get(
            "title",
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

        action = request.POST.get(
            "action"
        )

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )


        # ==================================================
        # ROLE-SPECIFIC ACTION VALIDATION
        # ==================================================

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
                {
                    "categories": categories,
                    "tags": tags,
                },
            )


        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/create_article.html",
                {
                    "categories": categories,
                    "tags": tags,
                },
            )


        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/create_article.html",
                {
                    "categories": categories,
                    "tags": tags,
                },
            )


        category = get_object_or_404(
            Category,
            id=category_id,
        )


        with transaction.atomic():

            base_slug = slugify(
                title
            ) or "article"

            slug = base_slug
            counter = 1

            while Article.objects.filter(
                slug=slug
            ).exists():

                slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1


            article = Article.objects.create(
                title=title,
                slug=slug,
                category=category,
                author=request.user,
                content=content,
                featured_image=featured_image,
                draft_type=Article.DraftType.NORMAL,
            )


            article.tags.set(
                tag_ids
            )


            for image in attachments:

                ArticleAttachment.objects.create(
                    article=article,
                    image=image,
                )


            # ==================================================
            # EDITOR SUBMISSION
            # ==================================================

            if (
                request.user.role == User.Role.EDITOR
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


            # ==================================================
            # EIC DIRECT PUBLICATION
            # ==================================================

            elif (
                request.user.role == User.Role.EIC
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


        if (
            request.user.role == User.Role.EDITOR
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
            request.user.role == User.Role.EIC
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
        {
            "categories": categories,
            "tags": tags,
        },
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
        )
        .prefetch_related(
            "article__attachments",
            "article__tags",
            "snapshot_attachments",
        )
    )

    if search_query:

        submissions = submissions.filter(
            Q(
                snapshot_title__icontains=search_query
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
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                article__tags__name__icontains=search_query
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
                "article__source_article",
                "submitted_by",
            ),
            id=submission_id,
        )


        if submission.status != Submission.Status.PENDING:

            messages.warning(
                request,
                "This submission has already been reviewed.",
            )

            return redirect(
                "pending_submissions"
            )


        article = Article.objects.select_for_update().get(
            id=submission.article_id
        )


        # ==================================================
        # APPROVE
        # ==================================================

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


                original_article.title = article.title
                original_article.category = article.category
                original_article.content = article.content
                original_article.featured_image = (
                    article.featured_image
                )
                original_article.is_published = True
                original_article.is_archived = False
                original_article.archived_at = None

                original_article.save()


                original_article.tags.set(
                    article.tags.all()
                )


                original_article.attachments.all().delete()


                for attachment in article.attachments.all():

                    ArticleAttachment.objects.create(
                        article=original_article,
                        image=attachment.image,
                        caption=attachment.caption,
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
                        f'"{original_article.title}" was approved '
                        f'and is now published.'
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

                    content_report.resolved_at = (
                        timezone.now()
                    )

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
                            f'"{original_article.title}" was approved. '
                            f'Your content report has been resolved.'
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
                        f'was approved and published.'
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

            if article.published_at is None:
                article.published_at = timezone.now()


            article.save(
                update_fields=[
                    "is_published",
                    "published_at",
                    "updated_at",
                ]
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


        # ==================================================
        # REJECT
        # ==================================================

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


        # ==================================================
        # REVISION
        # ==================================================

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

    selected_status = request.GET.get(
        "status",
        "ALL",
    )

    search_query = request.GET.get(
        "q",
        "",
    ).strip()


    submissions = (
        Submission.objects
        .filter(
            submitted_by=request.user,
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
        )
        .prefetch_related(
            "article__attachments",
            "article__tags",
            "snapshot_attachments",
        )
    )


    valid_statuses = {
        Submission.Status.PENDING,
        Submission.Status.APPROVED,
        Submission.Status.REJECTED,
        Submission.Status.REVISION,
    }


    if selected_status in valid_statuses:

        submissions = submissions.filter(
            status=selected_status
        )


    if search_query:

        submissions = submissions.filter(
            Q(
                snapshot_title__icontains=search_query
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
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                article__tags__name__icontains=search_query
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
        )
        .prefetch_related(
            "article__attachments",
            "article__tags",
            "snapshot_attachments",
        ),
        id=submission_id,
        submitted_by=request.user,
    )


    if submission.status != Submission.Status.REVISION:

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


    if request.method == "POST":

        title = request.POST.get(
            "title",
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

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        remove_attachment_ids = request.POST.getlist(
            "remove_attachments"
        )


        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/revise_submission.html",
                {
                    "submission": submission,
                    "article": article,
                    "categories": categories,
                    "tags": tags,
                },
            )


        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/revise_submission.html",
                {
                    "submission": submission,
                    "article": article,
                    "categories": categories,
                    "tags": tags,
                },
            )


        category = get_object_or_404(
            Category,
            id=category_id,
        )


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


            if locked_submission.resubmissions.exists():

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


            article = Article.objects.select_for_update().get(
                id=locked_submission.article_id
            )


            base_slug = slugify(
                title
            ) or "article"

            slug = base_slug
            counter = 1


            while (
                Article.objects
                .filter(
                    slug=slug
                )
                .exclude(
                    id=article.id
                )
                .exists()
            ):

                slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1


            article.title = title
            article.slug = slug
            article.category = category
            article.content = content


            if featured_image:

                article.featured_image = (
                    featured_image
                )


            article.save()


            article.tags.set(
                tag_ids
            )


            if remove_attachment_ids:

                ArticleAttachment.objects.filter(
                    id__in=remove_attachment_ids,
                    article=article,
                ).delete()


            for image in attachments:

                ArticleAttachment.objects.create(
                    article=article,
                    image=image,
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


        messages.success(
            request,
            (
                f'"{article.title}" was revised '
                f'and resubmitted successfully.'
            ),
        )


        return redirect(
            "my_submissions"
        )


    return render(
        request,
        "publications/revise_submission.html",
        {
            "submission": submission,
            "article": article,
            "categories": categories,
            "tags": tags,
        },
    )


@publication_role_required(
    User.Role.EDITOR
)
def resubmitted_submissions(request):

    submissions = (
        Submission.objects
        .filter(
            submitted_by=request.user,
            resubmission_of__isnull=False,
        )
        .select_related(
            "article",
            "article__category",
            "resubmission_of",
        )
        .prefetch_related(
            "article__attachments",
            "article__tags",
            "snapshot_attachments",
            "resubmission_of__snapshot_attachments",
        )
        .order_by(
            "-submitted_at"
        )
    )


    return render(
        request,
        "publications/resubmitted_submissions.html",
        {
            "submissions": submissions,
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
        )
        .prefetch_related(
            "attachments",
            "tags",
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
                content__icontains=search_query
            )
            | Q(
                category__name__icontains=search_query
            )
            | Q(
                tags__name__icontains=search_query
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

        edit_request_drafts = Article.objects.none()


    return render(
        request,
        "publications/my_drafts.html",
        {
            "drafts": drafts,
            "normal_drafts": normal_drafts,
            "edit_request_drafts": edit_request_drafts,
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
        )
        .prefetch_related(
            "attachments",
            "tags",
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
            "The EIC cannot directly manage Editor edit-request drafts."
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


    if request.method == "POST":

        title = request.POST.get(
            "title",
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

        action = request.POST.get(
            "action"
        )

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        remove_attachment_ids = request.POST.getlist(
            "remove_attachments"
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

            return redirect(
                "my_drafts"
            )


        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return redirect(
                "my_drafts"
            )


        category = get_object_or_404(
            Category,
            id=category_id,
        )


        with transaction.atomic():

            locked_article = get_object_or_404(
                Article.objects
                .select_for_update()
                .select_related(
                    "source_article"
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
                request.user.role == User.Role.EIC
                and locked_article.draft_type
                != Article.DraftType.NORMAL
            ):

                return HttpResponseForbidden(
                    "The EIC cannot directly manage Editor edit-request drafts."
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
                        status=EditRequest.Status.APPROVED,
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


            base_slug = slugify(
                title
            ) or "article"


            if (
                locked_article.draft_type
                == Article.DraftType.EDIT_REQUEST
            ):

                base_slug = (
                    f"{base_slug}-edit-draft-"
                    f"{locked_article.id}"
                )


            slug = base_slug
            counter = 1


            while (
                Article.objects
                .filter(
                    slug=slug
                )
                .exclude(
                    id=locked_article.id
                )
                .exists()
            ):

                slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1


            locked_article.title = title
            locked_article.slug = slug
            locked_article.category = category
            locked_article.content = content


            if featured_image:

                locked_article.featured_image = (
                    featured_image
                )


            locked_article.save()


            locked_article.tags.set(
                tag_ids
            )


            if remove_attachment_ids:

                ArticleAttachment.objects.filter(
                    id__in=remove_attachment_ids,
                    article=locked_article,
                ).delete()


            for image in attachments:

                ArticleAttachment.objects.create(
                    article=locked_article,
                    image=image,
                )


            # ==================================================
            # EDITOR SUBMISSION
            # ==================================================

            if (
                request.user.role == User.Role.EDITOR
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


            # ==================================================
            # EIC DIRECT PUBLICATION
            # ==================================================

            elif (
                request.user.role == User.Role.EIC
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


        if (
            request.user.role == User.Role.EDITOR
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
            request.user.role == User.Role.EIC
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
        {
            "article": article,
            "categories": categories,
            "tags": tags,
        },
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
            "tags",
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
            "tags",
        ),
        id=article_id,
        author=request.user,
        is_published=True,
        is_archived=False,
        draft_type=Article.DraftType.NORMAL,
    )


    categories = Category.objects.all()
    tags = Tag.objects.all()


    if request.method == "POST":

        title = request.POST.get(
            "title",
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

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        remove_attachment_ids = request.POST.getlist(
            "remove_attachments"
        )


        if not title:

            messages.error(
                request,
                "Article title is required.",
            )

            return render(
                request,
                "publications/edit_published_article.html",
                {
                    "article": article,
                    "categories": categories,
                    "tags": tags,
                },
            )


        if not category_id:

            messages.error(
                request,
                "Please select a category.",
            )

            return render(
                request,
                "publications/edit_published_article.html",
                {
                    "article": article,
                    "categories": categories,
                    "tags": tags,
                },
            )


        category = get_object_or_404(
            Category,
            id=category_id,
        )


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


            base_slug = slugify(
                title
            ) or "article"

            slug = base_slug
            counter = 1


            while (
                Article.objects
                .filter(
                    slug=slug
                )
                .exclude(
                    id=article.id
                )
                .exists()
            ):

                slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1


            article.title = title
            article.slug = slug
            article.category = category
            article.content = content


            if featured_image:

                article.featured_image = (
                    featured_image
                )


            article.save()


            article.tags.set(
                tag_ids
            )


            if remove_attachment_ids:

                ArticleAttachment.objects.filter(
                    article=article,
                    id__in=remove_attachment_ids,
                ).delete()


            for image in attachments:

                ArticleAttachment.objects.create(
                    article=article,
                    image=image,
                )


        messages.success(
            request,
            (
                f'"{article.title}" was updated '
                f'successfully.'
            ),
        )


        return redirect(
            "published_articles"
        )


    return render(
        request,
        "publications/edit_published_article.html",
        {
            "article": article,
            "categories": categories,
            "tags": tags,
        },
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
                        status=DeletionRequest.Status.PENDING,
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
                article__content__icontains=search_query
            )
            | Q(
                article__category__name__icontains=search_query
            )
            | Q(
                reason__icontains=search_query
            )
        )


    return render(
        request,
        "publications/my_edit_requests.html",
        {
            "edit_requests": requests,
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
                "draft_article",
                "requested_by",
            ),
            id=request_id,
        )


        if edit_request.status != EditRequest.Status.PENDING:

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
                    draft_type=Article.DraftType.EDIT_REQUEST,
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
                    status=DeletionRequest.Status.PENDING,
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


            base_slug = (
                f"{original_article.slug}-edit-"
                f"{edit_request.id}"
            )

            edit_draft_slug = base_slug
            counter = 1


            while Article.objects.filter(
                slug=edit_draft_slug
            ).exists():

                edit_draft_slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1


            edit_draft = Article.objects.create(
                title=original_article.title,
                slug=edit_draft_slug,
                category=original_article.category,
                author=original_article.author,
                content=original_article.content,
                featured_image=(
                    original_article.featured_image
                ),
                draft_type=Article.DraftType.EDIT_REQUEST,
                source_article=original_article,
                is_published=False,
                is_archived=False,
            )


            edit_draft.tags.set(
                original_article.tags.all()
            )


            for attachment in (
                original_article.attachments.all()
            ):

                ArticleAttachment.objects.create(
                    article=edit_draft,
                    image=attachment.image,
                    caption=attachment.caption,
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
                    f'A revision draft is now available.'
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
                        f'deletion of "{locked_article.title}".'
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


    if search_query:

        requests = requests.filter(
            Q(
                article__title__icontains=search_query
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
            article.archived_at = (
                timezone.now()
            )


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


        if report.status != ContentReport.Status.OPEN:

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


        if report.status != ContentReport.Status.OPEN:

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


        if report.status != ContentReport.Status.OPEN:

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
                (
                    "This article is already "
                    "archived."
                ),
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


        if (
            original_article.author.role
            != User.Role.EDITOR
        ):

            messages.warning(
                request,
                (
                    "This corrective revision workflow "
                    "currently requires the published "
                    "article to belong to an Editor."
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
                draft_type=Article.DraftType.EDIT_REQUEST,
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
                    "Revision required by the Editor in Chief "
                    f"because of Staff Content Report #{report.id}."
                ),
                status=EditRequest.Status.APPROVED,
                reviewer_notes=staff_notes,
                reviewed_at=timezone.now(),
            )
        )


        base_slug = (
            f"{original_article.slug}-"
            f"report-revision-{report.id}"
        )

        edit_draft_slug = base_slug
        counter = 1


        while Article.objects.filter(
            slug=edit_draft_slug
        ).exists():

            edit_draft_slug = (
                f"{base_slug}-{counter}"
            )

            counter += 1


        edit_draft = Article.objects.create(
            title=original_article.title,
            slug=edit_draft_slug,
            category=original_article.category,
            author=original_article.author,
            content=original_article.content,
            featured_image=(
                original_article.featured_image
            ),
            draft_type=Article.DraftType.EDIT_REQUEST,
            source_article=original_article,
            is_published=False,
            is_archived=False,
        )


        edit_draft.tags.set(
            original_article.tags.all()
        )


        for attachment in (
            original_article.attachments.all()
        ):

            ArticleAttachment.objects.create(
                article=edit_draft,
                image=attachment.image,
                caption=attachment.caption,
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
            "tags",
        )
    )


    if search_query:

        articles = articles.filter(
            Q(
                title__icontains=search_query
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

            article.published_at = timezone.now()


        article.save(
            update_fields=[
                "is_archived",
                "is_published",
                "archived_at",
                "published_at",
                "updated_at",
            ]
        )


        if article.author.role == User.Role.EDITOR:

            notify_user(
                article.author,
                Notification.Type.GENERAL,
                (
                    f'The archived article "{article.title}" '
                    f'was restored by the Editor in Chief.'
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