from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Q

from .models import (
    Article,
    ArticleAttachment,
    Category,
    EditRequest,
    Submission,
    Tag,
)


@login_required
def create_article(request):

    if request.user.role not in ["EDITOR", "EIC"]:
        return redirect("dashboard")

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":

        title = request.POST.get("title")
        category_id = request.POST.get("category")
        content = request.POST.get("content")
        tag_ids = request.POST.getlist("tags")
        action = request.POST.get("action")

        featured_image = request.FILES.get("featured_image")
        attachments = request.FILES.getlist("attachments")

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        base_slug = slugify(title) or "article"
        slug = base_slug
        counter = 1

        while Article.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
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

        article.tags.set(tag_ids)

        for image in attachments:
            ArticleAttachment.objects.create(
                article=article,
                image=image,
            )

        if action == "submit":

            submission = Submission.objects.create(
                article=article,
                submitted_by=request.user,
                status=Submission.Status.PENDING,
            )

            submission.capture_article_snapshot()

        return redirect("dashboard")

    return render(
        request,
        "publications/create_article.html",
        {
            "categories": categories,
            "tags": tags,
        },
    )


@login_required
def pending_submissions(request):

    if request.user.role != "EIC":
        return HttpResponseForbidden(
            "You do not have permission to view this page."
        )

    search_query = request.GET.get("q", "").strip()

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
            Q(snapshot_title__icontains=search_query)
            | Q(snapshot_content__icontains=search_query)
            | Q(snapshot_category_name__icontains=search_query)
            | Q(article__title__icontains=search_query)
            | Q(article__content__icontains=search_query)
            | Q(article__category__name__icontains=search_query)
            | Q(article__tags__name__icontains=search_query)
            | Q(submitted_by__username__icontains=search_query)
        )

    submissions = (
        submissions
        .order_by("-submitted_at")
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


@login_required
def review_submission(request, submission_id):

    if request.user.role != "EIC":
        return HttpResponseForbidden(
            "You do not have permission to review submissions."
        )

    submission = get_object_or_404(
        Submission.objects.select_related(
            "article",
            "article__source_article",
        ),
        id=submission_id,
    )

    if submission.status != Submission.Status.PENDING:
        return HttpResponseForbidden(
            "This submission has already been reviewed."
        )

    if request.method != "POST":
        return redirect("pending_submissions")

    action = request.POST.get("action")

    reviewer_notes = request.POST.get(
        "reviewer_notes",
        "",
    ).strip()

    article = submission.article

    if action == "approve":

        # --------------------------------------------------
        # EDIT REQUEST DRAFT APPROVAL
        # --------------------------------------------------

        if article.draft_type == Article.DraftType.EDIT_REQUEST:

            if not article.source_article:
                return HttpResponseForbidden(
                    "This edit draft is not connected to an original article."
                )

            with transaction.atomic():

                original_article = Article.objects.select_for_update().get(
                    id=article.source_article_id
                )

                edit_request = EditRequest.objects.filter(
                    draft_article=article,
                    status=EditRequest.Status.APPROVED,
                ).first()

                if edit_request is None:
                    edit_request = (
                        EditRequest.objects
                        .filter(
                            article=original_article,
                            requested_by=article.author,
                            status=EditRequest.Status.APPROVED,
                            draft_article__isnull=True,
                        )
                        .order_by("-reviewed_at", "-created_at")
                        .first()
                    )

                    if edit_request:
                        edit_request.draft_article = article
                        edit_request.save(
                            update_fields=["draft_article"]
                        )

                if edit_request is None:
                    return HttpResponseForbidden(
                        "No approved edit request is connected to this draft."
                    )

                original_article.title = article.title
                original_article.category = article.category
                original_article.content = article.content
                original_article.featured_image = article.featured_image

                original_article.is_published = True
                original_article.is_archived = False

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

                submission.status = Submission.Status.APPROVED
                submission.reviewer_notes = reviewer_notes
                submission.reviewed_at = timezone.now()
                submission.save()

                edit_request.status = EditRequest.Status.COMPLETED
                edit_request.save(
                    update_fields=["status"]
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

            return redirect("pending_submissions")

        # --------------------------------------------------
        # NORMAL ARTICLE APPROVAL
        # --------------------------------------------------

        submission.status = Submission.Status.APPROVED

        article.is_published = True

        if article.published_at is None:
            article.published_at = timezone.now()

        article.save()

    elif action == "reject":

        submission.status = Submission.Status.REJECTED

    elif action == "revision":

        submission.status = Submission.Status.REVISION

    else:

        return redirect("pending_submissions")

    submission.reviewer_notes = reviewer_notes
    submission.reviewed_at = timezone.now()
    submission.save()

    return redirect("pending_submissions")


@login_required
def my_submissions(request):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to view this page."
        )

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
        "PENDING",
        "APPROVED",
        "REJECTED",
        "REVISION",
    }

    if selected_status in valid_statuses:
        submissions = submissions.filter(
            status=selected_status
        )

    if search_query:
        submissions = submissions.filter(
            Q(snapshot_title__icontains=search_query)
            | Q(snapshot_content__icontains=search_query)
            | Q(snapshot_category_name__icontains=search_query)
            | Q(article__title__icontains=search_query)
            | Q(article__content__icontains=search_query)
            | Q(article__category__name__icontains=search_query)
            | Q(article__tags__name__icontains=search_query)
        )

    submissions = (
        submissions
        .order_by("-submitted_at")
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


@login_required
def revise_submission(request, submission_id):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to revise this submission."
        )

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
        return HttpResponseForbidden(
            "This submission is not currently available for revision."
        )

    article = submission.article

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":

        title = request.POST.get("title")
        category_id = request.POST.get("category")
        content = request.POST.get("content")
        tag_ids = request.POST.getlist("tags")

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        remove_attachment_ids = request.POST.getlist(
            "remove_attachments"
        )

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        base_slug = slugify(title) or "article"
        slug = base_slug
        counter = 1

        while (
            Article.objects
            .filter(slug=slug)
            .exclude(id=article.id)
            .exists()
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1

        article.title = title
        article.slug = slug
        article.category = category
        article.content = content

        if featured_image:
            article.featured_image = featured_image

        article.save()

        article.tags.set(tag_ids)

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

        new_submission = Submission.objects.create(
            article=article,
            submitted_by=request.user,
            status=Submission.Status.PENDING,
            resubmission_of=submission,
        )

        new_submission.capture_article_snapshot()

        return redirect("my_submissions")

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


@login_required
def resubmitted_submissions(request):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to view this page."
        )

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
        .order_by("-submitted_at")
    )

    return render(
        request,
        "publications/resubmitted_submissions.html",
        {
            "submissions": submissions,
        },
    )


@login_required
def my_drafts(request):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to view this page."
        )

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

    if search_query:
        drafts = drafts.filter(
            Q(title__icontains=search_query)
            | Q(content__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(tags__name__icontains=search_query)
        )

    drafts = (
        drafts
        .order_by("-updated_at")
        .distinct()
    )

    normal_drafts = drafts.filter(
        draft_type=Article.DraftType.NORMAL
    )

    edit_request_drafts = drafts.filter(
        draft_type=Article.DraftType.EDIT_REQUEST
    )

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


@login_required
def edit_draft(request, article_id):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to edit this draft."
        )

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

    if article.draft_type == Article.DraftType.EDIT_REQUEST:

        approved_request_exists = EditRequest.objects.filter(
            article=article.source_article,
            requested_by=request.user,
            status=EditRequest.Status.APPROVED,
        ).exists()

        if not approved_request_exists:
            return HttpResponseForbidden(
                "This edit-request draft is no longer available."
            )

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":

        title = request.POST.get("title")
        category_id = request.POST.get("category")
        content = request.POST.get("content")
        tag_ids = request.POST.getlist("tags")
        action = request.POST.get("action")

        featured_image = request.FILES.get(
            "featured_image"
        )

        attachments = request.FILES.getlist(
            "attachments"
        )

        remove_attachment_ids = request.POST.getlist(
            "remove_attachments"
        )

        category = get_object_or_404(
            Category,
            id=category_id,
        )

        base_slug = slugify(title) or "article"

        if article.draft_type == Article.DraftType.EDIT_REQUEST:
            base_slug = f"{base_slug}-edit-draft-{article.id}"

        slug = base_slug
        counter = 1

        while (
            Article.objects
            .filter(slug=slug)
            .exclude(id=article.id)
            .exists()
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1

        article.title = title
        article.slug = slug
        article.category = category
        article.content = content

        if featured_image:
            article.featured_image = featured_image

        article.save()

        article.tags.set(tag_ids)

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

        if action == "submit":

            submission = Submission.objects.create(
                article=article,
                submitted_by=request.user,
                status=Submission.Status.PENDING,
            )

            submission.capture_article_snapshot()

            return redirect("my_submissions")

        return redirect("my_drafts")

    return render(
        request,
        "publications/edit_draft.html",
        {
            "article": article,
            "categories": categories,
            "tags": tags,
        },
    )


@login_required
def delete_draft(request, article_id):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to delete this draft."
        )

    article = get_object_or_404(
        Article,
        id=article_id,
        author=request.user,
        is_published=False,
        is_archived=False,
        submissions__isnull=True,
        draft_type=Article.DraftType.NORMAL,
    )

    if request.method == "POST":
        article.delete()

    return redirect("my_drafts")


@login_required
def published_articles(request):

    if request.user.role not in ["EDITOR", "EIC"]:
        return HttpResponseForbidden(
            "You do not have permission to view published articles."
        )

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

    if request.user.role == "EDITOR":
        articles = articles.filter(
            author=request.user
        )

    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query)
            | Q(content__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(tags__name__icontains=search_query)
            | Q(author__username__icontains=search_query)
        )

    articles = (
        articles
        .order_by("-published_at")
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


@login_required
def request_article_edit(request, article_id):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to request article edits."
        )

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
        return HttpResponseForbidden(
            "You already have an active edit request for this article."
        )

    if request.method == "POST":

        reason = request.POST.get(
            "reason",
            "",
        ).strip()

        if reason:

            EditRequest.objects.create(
                article=article,
                requested_by=request.user,
                reason=reason,
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


@login_required
def my_edit_requests(request):

    if request.user.role != "EDITOR":
        return HttpResponseForbidden(
            "You do not have permission to view this page."
        )

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
        .order_by("-created_at")
    )

    if search_query:
        requests = requests.filter(
            Q(article__title__icontains=search_query)
            | Q(article__content__icontains=search_query)
            | Q(article__category__name__icontains=search_query)
            | Q(reason__icontains=search_query)
        )

    return render(
        request,
        "publications/my_edit_requests.html",
        {
            "edit_requests": requests,
            "search_query": search_query,
        },
    )


@login_required
def eic_edit_requests(request):

    if request.user.role != "EIC":
        return HttpResponseForbidden(
            "You do not have permission to view edit requests."
        )

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
        .order_by("-created_at")
    )

    if search_query:
        requests = requests.filter(
            Q(article__title__icontains=search_query)
            | Q(article__content__icontains=search_query)
            | Q(article__category__name__icontains=search_query)
            | Q(requested_by__username__icontains=search_query)
            | Q(reason__icontains=search_query)
        )

    return render(
        request,
        "publications/eic_edit_requests.html",
        {
            "edit_requests": requests,
            "search_query": search_query,
        },
    )


@login_required
def review_edit_request(request, request_id):

    if request.user.role != "EIC":
        return HttpResponseForbidden(
            "You do not have permission to review edit requests."
        )

    edit_request = get_object_or_404(
        EditRequest.objects.select_related(
            "article",
            "draft_article",
        ),
        id=request_id,
        status=EditRequest.Status.PENDING,
    )

    if request.method != "POST":
        return redirect("eic_edit_requests")

    action = request.POST.get("action")

    reviewer_notes = request.POST.get(
        "reviewer_notes",
        "",
    ).strip()

    if action == "approve":

        original_article = edit_request.article

        existing_draft = Article.objects.filter(
            source_article=original_article,
            draft_type=Article.DraftType.EDIT_REQUEST,
            is_published=False,
            is_archived=False,
        ).exists()

        if existing_draft:
            return HttpResponseForbidden(
                "An active edit-request draft already exists "
                "for this article."
            )

        with transaction.atomic():

            base_slug = (
                f"{original_article.slug}-edit-{edit_request.id}"
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
                featured_image=original_article.featured_image,
                draft_type=Article.DraftType.EDIT_REQUEST,
                source_article=original_article,
                is_published=False,
                is_archived=False,
            )

            edit_draft.tags.set(
                original_article.tags.all()
            )

            for attachment in original_article.attachments.all():

                ArticleAttachment.objects.create(
                    article=edit_draft,
                    image=attachment.image,
                    caption=attachment.caption,
                )

            edit_request.status = EditRequest.Status.APPROVED
            edit_request.reviewer_notes = reviewer_notes
            edit_request.reviewed_at = timezone.now()
            edit_request.draft_article = edit_draft

            edit_request.save()

    elif action == "reject":

        edit_request.status = EditRequest.Status.REJECTED
        edit_request.reviewer_notes = reviewer_notes
        edit_request.reviewed_at = timezone.now()

        edit_request.save()

    else:

        return redirect(
            "eic_edit_requests"
        )

    return redirect(
        "eic_edit_requests"
    )