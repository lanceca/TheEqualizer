from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseForbidden
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from analytics.models import ArticleDailyAnalytics
from publications.models import Article


# ==========================================================
# ANALYTICS HELPERS
# ==========================================================


def increment_daily_article_analytics(
    article,
    *,
    views=0,
    reactions=0,
    shares=0,
):
    """
    Increment the current Manila-calendar-day analytics row
    for a published article.

    Lifetime counters remain stored on Article itself.
    This model provides historical daily trend data.
    """

    today = timezone.localdate()

    with transaction.atomic():

        daily_analytics, created = (
            ArticleDailyAnalytics.objects
            .select_for_update()
            .get_or_create(
                article=article,
                date=today,
            )
        )

        updates = {}

        if views:
            updates["views"] = F("views") + views

        if reactions:
            updates["reactions"] = (
                F("reactions") + reactions
            )

        if shares:
            updates["shares"] = (
                F("shares") + shares
            )

        if updates:

            ArticleDailyAnalytics.objects.filter(
                id=daily_analytics.id
            ).update(
                **updates
            )


# ==========================================================
# HOME PAGE
# ==========================================================


def home(request):

    published_articles = (
        Article.objects
        .filter(
            draft_type=Article.DraftType.NORMAL,
            is_published=True,
            is_archived=False,
        )
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "tags",
        )
        .order_by(
            "-published_at",
            "-created_at",
        )
    )

    return render(
        request,
        "home/home.html",
        {
            "published_articles": (
                published_articles
            ),
        },
    )


# ==========================================================
# PUBLIC ARTICLE DETAIL
# ==========================================================


def article_detail(
    request,
    slug,
):

    article = get_object_or_404(
        Article.objects
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "tags",
            "attachments",
        ),
        slug=slug,
        draft_type=Article.DraftType.NORMAL,
        is_published=True,
        is_archived=False,
    )

    # ======================================================
    # VIEW TRACKING
    #
    # Count only one view per article for the current
    # browser session.
    # ======================================================

    viewed_articles = request.session.get(
        "viewed_articles",
        [],
    )

    if article.id not in viewed_articles:

        with transaction.atomic():

            Article.objects.filter(
                id=article.id
            ).update(
                view_count=F(
                    "view_count"
                ) + 1
            )

            increment_daily_article_analytics(
                article,
                views=1,
            )

        viewed_articles.append(
            article.id
        )

        request.session[
            "viewed_articles"
        ] = viewed_articles

        article.refresh_from_db(
            fields=[
                "view_count",
            ]
        )

    reacted_articles = request.session.get(
        "reacted_articles",
        [],
    )

    shared_articles = request.session.get(
        "shared_articles",
        [],
    )

    return render(
        request,
        "home/article_detail.html",
        {
            "article": article,

            "has_reacted": (
                article.id
                in reacted_articles
            ),

            "has_shared": (
                article.id
                in shared_articles
            ),
        },
    )


# ==========================================================
# ARTICLE REACTION
# ==========================================================


def react_to_article(
    request,
    slug,
):

    if request.method != "POST":

        return HttpResponseForbidden(
            "This action requires a POST request."
        )

    article = get_object_or_404(
        Article,
        slug=slug,
        draft_type=Article.DraftType.NORMAL,
        is_published=True,
        is_archived=False,
    )

    reacted_articles = request.session.get(
        "reacted_articles",
        [],
    )

    if article.id in reacted_articles:

        messages.info(
            request,
            "You have already reacted to this article.",
        )

        return redirect(
            "article_detail",
            slug=article.slug,
        )

    with transaction.atomic():

        Article.objects.filter(
            id=article.id
        ).update(
            reaction_count=F(
                "reaction_count"
            ) + 1
        )

        increment_daily_article_analytics(
            article,
            reactions=1,
        )

    reacted_articles.append(
        article.id
    )

    request.session[
        "reacted_articles"
    ] = reacted_articles

    messages.success(
        request,
        "Your reaction was recorded.",
    )

    return redirect(
        "article_detail",
        slug=article.slug,
    )


# ==========================================================
# ARTICLE SHARE TRACKING
# ==========================================================


def share_article(
    request,
    slug,
):

    if request.method != "POST":

        return HttpResponseForbidden(
            "This action requires a POST request."
        )

    article = get_object_or_404(
        Article,
        slug=slug,
        draft_type=Article.DraftType.NORMAL,
        is_published=True,
        is_archived=False,
    )

    shared_articles = request.session.get(
        "shared_articles",
        [],
    )

    if article.id not in shared_articles:

        with transaction.atomic():

            Article.objects.filter(
                id=article.id
            ).update(
                share_count=F(
                    "share_count"
                ) + 1
            )

            increment_daily_article_analytics(
                article,
                shares=1,
            )

        shared_articles.append(
            article.id
        )

        request.session[
            "shared_articles"
        ] = shared_articles

    return redirect(
        "article_detail",
        slug=article.slug,
    )