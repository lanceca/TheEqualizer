from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
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
        )

        article.tags.set(tag_ids)

        for image in attachments:
            ArticleAttachment.objects.create(
                article=article,
                image=image,
            )

        if action == "submit":
            Submission.objects.create(
                article=article,
                submitted_by=request.user,
                status=Submission.Status.PENDING,
            )

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
        )
        .prefetch_related(
            "article__attachments",
            "article__tags",
        )
    )

    if search_query:
        submissions = submissions.filter(
            Q(article__title__icontains=search_query)
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
        Submission,
        id=submission_id,
    )

    if request.method == "POST":

        action = request.POST.get("action")
        reviewer_notes = request.POST.get(
            "reviewer_notes",
            "",
        )

        if action == "approve":

            submission.status = Submission.Status.APPROVED

            submission.article.is_published = True
            submission.article.published_at = timezone.now()

            submission.article.save()

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

    selected_status = request.GET.get("status", "ALL")
    search_query = request.GET.get("q", "").strip()

    submissions = (
        Submission.objects
        .filter(
            submitted_by=request.user,
            resubmissions__isnull=True,
        )
        .select_related(
            "article",
            "article__category",
        )
        .prefetch_related(
            "article__attachments",
            "article__tags",
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
            Q(article__title__icontains=search_query)
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

        featured_image = request.FILES.get("featured_image")
        attachments = request.FILES.getlist("attachments")

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

        Submission.objects.create(
            article=article,
            submitted_by=request.user,
            status=Submission.Status.PENDING,
            resubmission_of=submission,
        )

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

    search_query = request.GET.get("q", "").strip()

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

    return render(
        request,
        "publications/my_drafts.html",
        {
            "drafts": drafts,
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
        .select_related("category")
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

        if action == "submit":

            Submission.objects.create(
                article=article,
                submitted_by=request.user,
                status=Submission.Status.PENDING,
            )

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

    search_query = request.GET.get("q", "").strip()

    articles = (
        Article.objects
        .filter(
            is_published=True,
            is_archived=False,
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
    )

    existing_request = EditRequest.objects.filter(
        article=article,
        requested_by=request.user,
        status=EditRequest.Status.PENDING,
    ).exists()

    if existing_request:
        return HttpResponseForbidden(
            "You already have a pending edit request for this article."
        )

    if request.method == "POST":

        reason = request.POST.get("reason", "").strip()

        if reason:
            EditRequest.objects.create(
                article=article,
                requested_by=request.user,
                reason=reason,
            )

            return redirect("my_edit_requests")

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

    search_query = request.GET.get("q", "").strip()

    requests = (
        EditRequest.objects
        .filter(
            requested_by=request.user
        )
        .select_related(
            "article",
            "article__category",
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

    search_query = request.GET.get("q", "").strip()

    requests = (
        EditRequest.objects
        .filter(
            status=EditRequest.Status.PENDING
        )
        .select_related(
            "article",
            "article__category",
            "requested_by",
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
        EditRequest,
        id=request_id,
        status=EditRequest.Status.PENDING,
    )

    if request.method == "POST":

        action = request.POST.get("action")
        reviewer_notes = request.POST.get(
            "reviewer_notes",
            "",
        ).strip()

        if action == "approve":
            edit_request.status = EditRequest.Status.APPROVED

        elif action == "reject":
            edit_request.status = EditRequest.Status.REJECTED

        else:
            return redirect("eic_edit_requests")

        edit_request.reviewer_notes = reviewer_notes
        edit_request.reviewed_at = timezone.now()
        edit_request.save()

    return redirect("eic_edit_requests")