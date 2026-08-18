from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import (
    Article,
    ArticleAttachment,
    Category,
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

        base_slug = slugify(title)
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
        "article__attachments"
    )
)

    return render(
        request,
        "publications/pending_submissions.html",
        {
            "submissions": submissions,
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