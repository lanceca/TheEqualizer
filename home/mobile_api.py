from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analytics.models import ArticleDailyAnalytics

from publications.models import (
    AboutUsPage,
    Article,
    Category,
    DigitalPublication,
    PeopleProfile,
    SchoolAdvertisement,
)



def _increment_daily_article_analytics(
    article,
    *,
    views=0,
    reactions=0,
    shares=0,
):
    """Keep mobile engagement in the same daily analytics table as the website."""
    today = timezone.localdate()

    with transaction.atomic():
        daily_analytics, _ = (
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
            updates["reactions"] = F("reactions") + reactions

        if shares:
            updates["shares"] = F("shares") + shares

        if updates:
            ArticleDailyAnalytics.objects.filter(
                id=daily_analytics.id
            ).update(**updates)


def _article_pdf_download_count(article):
    """Return the article's existing unique PDF download total."""
    return (
        ArticleDailyAnalytics.objects
        .filter(article=article)
        .aggregate(total=Sum("downloads"))["total"]
        or 0
    )


def _decrement_article_reaction_analytics(article):
    """
    Remove one recorded reaction from the article's analytics history.

    The most recent positive analytics row is reduced so the aggregate
    reaction total used by Adviser analytics stays aligned with the
    article's current like count after an Unlike action.
    """
    with transaction.atomic():
        analytics_row = (
            ArticleDailyAnalytics.objects
            .select_for_update()
            .filter(
                article=article,
                reactions__gt=0,
            )
            .order_by("-date")
            .first()
        )

        if analytics_row:
            ArticleDailyAnalytics.objects.filter(
                id=analytics_row.id,
                reactions__gt=0,
            ).update(
                reactions=F("reactions") - 1
            )


def _mobile_engagement_state(request, article):
    reacted_articles = request.session.get(
        "mobile_reacted_articles",
        [],
    )
    shared_articles = request.session.get(
        "mobile_shared_articles",
        [],
    )

    return {
        "has_reacted": article.id in reacted_articles,
        "has_shared": article.id in shared_articles,
    }


def _absolute_file_url(request, file_field):
    if not file_field:
        return ""

    try:
        url = file_field.url
    except (ValueError, AttributeError):
        return ""

    return request.build_absolute_uri(url)


def _article_queryset():
    """Shared article relations used by mobile reader endpoints."""
    return (
        Article.objects
        .filter(
            draft_type=Article.DraftType.NORMAL,
        )
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "tags",
            "attachments",
            "video_attachments",
            "contributors",
            "contributors__user",
        )
    )


def _published_articles():
    """Active public articles used by Home and Category screens."""
    return (
        _article_queryset()
        .filter(
            is_published=True,
            is_archived=False,
        )
        .order_by(
            "-published_at",
            "-created_at",
        )
    )


def _public_readable_articles():
    """
    Match the website reader rule.

    A currently published article is readable, and a previously published
    archived article remains readable from the public archive.
    """
    return (
        _article_queryset()
        .filter(
            Q(
                is_published=True,
                is_archived=False,
            )
            | Q(
                is_archived=True,
                published_at__isnull=False,
            )
        )
    )


def _archived_articles():
    return (
        _article_queryset()
        .filter(
            is_archived=True,
            published_at__isnull=False,
        )
        .order_by(
            "-published_at",
            "-id",
        )
    )


def _author_payload(request, user):
    return {
        "username": user.username,
        "display_name": user.get_full_name().strip() or user.username,
        "profile_picture_url": _absolute_file_url(
            request,
            getattr(user, "profile_picture", None),
        ),
    }


def _mobile_article_filters(request):
    """Resolve keyword and inclusive publication-date filters."""
    search_query = request.GET.get("q", "").strip()[:100]
    start_value = request.GET.get("start", "").strip()[:10]
    end_value = request.GET.get("end", "").strip()[:10]

    start_date = parse_date(start_value) if start_value else None
    end_date = parse_date(end_value) if end_value else None
    filter_error = ""

    if start_value and start_date is None:
        filter_error = "Choose a valid From date."
        start_value = ""

    if end_value and end_date is None:
        filter_error = filter_error or "Choose a valid To date."
        end_value = ""

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        filter_error = "The From date cannot be later than the To date."
        start_date = None
        end_date = None
        start_value = ""
        end_value = ""

    return {
        "query": search_query,
        "start_date": start_date,
        "end_date": end_date,
        "start_value": start_value,
        "end_value": end_value,
        "filter_error": filter_error,
    }


def _apply_mobile_article_filters(queryset, filters):
    search_query = filters["query"]

    if search_query:
        for term in [
            value
            for value in search_query.split()
            if value
        ][:8]:
            queryset = queryset.filter(
                Q(title__icontains=term)
                | Q(subtitle__icontains=term)
                | Q(excerpt__icontains=term)
                | Q(content__icontains=term)
                | Q(author__username__icontains=term)
                | Q(tags__name__icontains=term)
            )

        queryset = queryset.distinct()

    if filters["start_date"] is not None:
        queryset = queryset.filter(
            published_at__date__gte=filters["start_date"]
        )

    if filters["end_date"] is not None:
        queryset = queryset.filter(
            published_at__date__lte=filters["end_date"]
        )

    return queryset


def _article_hero_image_url(request, article):
    if article.featured_image:
        return _absolute_file_url(request, article.featured_image)

    first_attachment = next(iter(article.attachments.all()), None)

    if first_attachment:
        return _absolute_file_url(request, first_attachment.image)

    return ""


def _article_summary_payload(request, article):
    published_value = article.published_at or article.created_at

    return {
        "id": article.id,
        "title": article.title,
        "subtitle": article.subtitle,
        "excerpt": article.excerpt,
        "slug": article.slug,
        "category": {
            "id": article.category_id,
            "name": article.category.name,
            "slug": article.category.slug,
        },
        "author": _author_payload(request, article.author),
        "published_at": (
            published_value.isoformat()
            if published_value
            else None
        ),
        "updated_at": article.updated_at.isoformat(),
        "version_number": article.version_number,
        "is_archived": article.is_archived,
        "archived_at": (
            article.archived_at.isoformat()
            if article.archived_at
            else None
        ),
        "attachment_mode": article.attachment_mode,
        "hero_image_url": _article_hero_image_url(request, article),
        "featured_image_caption": article.featured_image_caption,
        "featured_image_credit": article.featured_image_credit,
        "tags": [
            {
                "name": tag.name,
                "slug": tag.slug,
            }
            for tag in article.tags.all()
        ],
        "engagement": {
            "views": article.view_count,
            "reactions": article.reaction_count,
            "shares": article.share_count,
        },
    }


def _article_detail_payload(request, article):
    payload = _article_summary_payload(request, article)
    payload["engagement"]["downloads"] = (
        _article_pdf_download_count(article)
    )

    payload.update(
        {
            "content": article.content,
            "featured_image_url": (
                _absolute_file_url(request, article.featured_image)
                if article.featured_image
                else ""
            ),
            "contributors": [
                {
                    "username": contributor.user.username,
                    "display_name": (
                        contributor.user.get_full_name().strip()
                        or contributor.user.username
                    ),
                    "profile_picture_url": _absolute_file_url(
                        request,
                        getattr(contributor.user, "profile_picture", None),
                    ),
                    "role": contributor.role,
                    "role_display": contributor.get_role_display(),
                }
                for contributor in article.contributors.all()
            ],
            "version_history_url": request.build_absolute_uri(
                f"/articles/{article.slug}/history/"
            ),
            "pdf_url": request.build_absolute_uri(
                f"/articles/{article.slug}/download-pdf/"
            ),
            "image_attachments": [
                {
                    "id": attachment.id,
                    "image_url": _absolute_file_url(
                        request,
                        attachment.image,
                    ),
                    "caption": attachment.caption,
                    "alt_text": attachment.alt_text,
                    "credit": attachment.credit,
                }
                for attachment in article.attachments.all()
            ],
            "video_attachments": [
                {
                    "id": attachment.id,
                    "video_url": _absolute_file_url(
                        request,
                        attachment.video,
                    ),
                    "caption": attachment.caption,
                    "credit": attachment.credit,
                }
                for attachment in article.video_attachments.all()
            ],
        }
    )

    return payload


def _school_update_payload(request, advertisement):
    return {
        "id": advertisement.id,
        "title": advertisement.title,
        "slug": advertisement.slug,
        "summary": advertisement.summary,
        "details": advertisement.details,
        "image_url": _absolute_file_url(
            request,
            advertisement.image,
        ),
        "updated_at": advertisement.updated_at.isoformat(),
    }


def _digital_publication_payload(
    request,
    publication,
    *,
    include_pdf=True,
):
    payload = {
        "id": publication.id,
        "title": publication.title,
        "slug": publication.slug,
        "volume": publication.volume,
        "issue_number": publication.issue_number,
        "publication_date": publication.publication_date.isoformat(),
        "description": publication.description,
        "cover_image_url": _absolute_file_url(
            request,
            publication.cover_image,
        ),
        "page_count": publication.page_count,
        "file_size": publication.file_size,
    }

    if include_pdf:
        payload["pdf_url"] = _absolute_file_url(
            request,
            publication.pdf_file,
        )

    return payload


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_api_health(request):
    return Response(
        {
            "status": "ok",
            "service": "The Equalizer Mobile API",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_home(request):
    latest_articles = list(_published_articles()[:12])

    school_updates = list(
        SchoolAdvertisement.objects
        .filter(is_active=True)
        .order_by("display_order", "-updated_at")[:4]
    )

    publications = list(
        DigitalPublication.objects
        .filter(status=DigitalPublication.Status.PUBLISHED)
        .order_by(
            "display_order",
            "-publication_date",
            "-created_at",
        )[:4]
    )

    return Response(
        {
            "latest_articles": [
                _article_summary_payload(request, article)
                for article in latest_articles
            ],
            "school_updates": [
                _school_update_payload(request, advertisement)
                for advertisement in school_updates
            ],
            "digital_publications": [
                _digital_publication_payload(
                    request,
                    publication,
                    include_pdf=False,
                )
                for publication in publications
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_categories(request):
    categories = (
        Category.objects
        .annotate(
            published_article_count=Count(
                "articles",
                filter=Q(
                    articles__draft_type=Article.DraftType.NORMAL,
                    articles__is_published=True,
                    articles__is_archived=False,
                ),
            )
        )
        .order_by("name")
    )

    return Response(
        {
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "description": category.description,
                    "article_count": category.published_article_count,
                }
                for category in categories
            ]
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_articles(request):
    articles = _published_articles()

    category_slug = request.GET.get("category", "").strip()
    filters = _mobile_article_filters(request)

    if category_slug:
        articles = articles.filter(category__slug=category_slug)

    articles = _apply_mobile_article_filters(articles, filters)

    try:
        limit = int(request.GET.get("limit", "50"))
    except (TypeError, ValueError):
        limit = 50

    limit = max(1, min(limit, 100))
    total_count = articles.count()
    articles = list(articles[:limit])

    return Response(
        {
            "count": total_count,
            "articles": [
                _article_summary_payload(request, article)
                for article in articles
            ],
            "filters": {
                "query": filters["query"],
                "start": filters["start_value"],
                "end": filters["end_value"],
                "filter_error": filters["filter_error"],
            },
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_archive(request):
    articles = _archived_articles()
    filters = _mobile_article_filters(request)

    category_value = request.GET.get("category", "").strip()

    if category_value:
        if category_value.isascii() and category_value.isdigit():
            articles = articles.filter(category_id=int(category_value))
        else:
            articles = articles.filter(category__slug=category_value)

    month_value = request.GET.get("month", "").strip()[:7]
    month_date = (
        parse_date(f"{month_value}-01")
        if len(month_value) == 7
        else None
    )

    if month_date is not None:
        articles = articles.filter(
            published_at__year=month_date.year,
            published_at__month=month_date.month,
        )
    else:
        month_value = ""

    articles = _apply_mobile_article_filters(articles, filters)

    try:
        limit = int(request.GET.get("limit", "100"))
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, 200))
    total_count = articles.count()
    articles = list(articles[:limit])

    return Response(
        {
            "count": total_count,
            "articles": [
                _article_summary_payload(request, article)
                for article in articles
            ],
            "filters": {
                "query": filters["query"],
                "category": category_value,
                "start": filters["start_value"],
                "end": filters["end_value"],
                "month": month_value,
                "filter_error": filters["filter_error"],
            },
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_article_detail(request, slug):
    article = get_object_or_404(
        _public_readable_articles(),
        slug=slug,
    )

    # Match the website's reader behavior: one view per article
    # for the current anonymous session.
    viewed_articles = request.session.get(
        "mobile_viewed_articles",
        [],
    )

    if article.id not in viewed_articles:
        with transaction.atomic():
            Article.objects.filter(
                id=article.id
            ).update(
                view_count=F("view_count") + 1
            )

            _increment_daily_article_analytics(
                article,
                views=1,
            )

        viewed_articles.append(article.id)
        request.session["mobile_viewed_articles"] = viewed_articles

        article.refresh_from_db(
            fields=["view_count"]
        )

    state = _mobile_engagement_state(
        request,
        article,
    )

    return Response(
        {
            "article": _article_detail_payload(
                request,
                article,
            ),
            **state,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def mobile_article_react(request, slug):
    article = get_object_or_404(
        _public_readable_articles(),
        slug=slug,
    )

    reacted_articles = request.session.get(
        "mobile_reacted_articles",
        [],
    )

    already_reacted = article.id in reacted_articles

    if already_reacted:
        with transaction.atomic():
            Article.objects.filter(
                id=article.id,
                reaction_count__gt=0,
            ).update(
                reaction_count=F("reaction_count") - 1
            )

            _decrement_article_reaction_analytics(
                article
            )

        reacted_articles = [
            article_id
            for article_id in reacted_articles
            if article_id != article.id
        ]
    else:
        with transaction.atomic():
            Article.objects.filter(
                id=article.id
            ).update(
                reaction_count=F("reaction_count") + 1
            )

            _increment_daily_article_analytics(
                article,
                reactions=1,
            )

        reacted_articles.append(article.id)

    request.session["mobile_reacted_articles"] = reacted_articles

    article.refresh_from_db(
        fields=[
            "view_count",
            "reaction_count",
            "share_count",
        ]
    )

    return Response(
        {
            "recorded": True,
            "has_reacted": not already_reacted,
            "engagement": {
                "views": article.view_count,
                "reactions": article.reaction_count,
                "shares": article.share_count,
                "downloads": _article_pdf_download_count(article),
            },
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def mobile_article_share(request, slug):
    article = get_object_or_404(
        _public_readable_articles(),
        slug=slug,
    )

    shared_articles = request.session.get(
        "mobile_shared_articles",
        [],
    )

    already_shared = article.id in shared_articles

    if not already_shared:
        with transaction.atomic():
            Article.objects.filter(
                id=article.id
            ).update(
                share_count=F("share_count") + 1
            )

            _increment_daily_article_analytics(
                article,
                shares=1,
            )

        shared_articles.append(article.id)
        request.session["mobile_shared_articles"] = shared_articles

    article.refresh_from_db(
        fields=[
            "view_count",
            "reaction_count",
            "share_count",
        ]
    )

    return Response(
        {
            "recorded": not already_shared,
            "has_shared": True,
            "engagement": {
                "views": article.view_count,
                "reactions": article.reaction_count,
                "shares": article.share_count,
                "downloads": _article_pdf_download_count(article),
            },
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_school_updates(request):
    advertisements = (
        SchoolAdvertisement.objects
        .filter(is_active=True)
        .order_by("display_order", "-updated_at")
    )

    return Response(
        {
            "school_updates": [
                _school_update_payload(request, advertisement)
                for advertisement in advertisements
            ]
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_school_update_detail(request, slug):
    advertisement = get_object_or_404(
        SchoolAdvertisement,
        slug=slug,
        is_active=True,
    )

    return Response(
        {
            "school_update": _school_update_payload(
                request,
                advertisement,
            )
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_digital_publications(request):
    publications = (
        DigitalPublication.objects
        .filter(status=DigitalPublication.Status.PUBLISHED)
        .order_by(
            "display_order",
            "-publication_date",
            "-created_at",
        )
    )

    return Response(
        {
            "digital_publications": [
                _digital_publication_payload(
                    request,
                    publication,
                    include_pdf=False,
                )
                for publication in publications
            ]
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_digital_publication_detail(request, slug):
    publication = get_object_or_404(
        DigitalPublication,
        slug=slug,
        status=DigitalPublication.Status.PUBLISHED,
    )

    return Response(
        {
            "digital_publication": _digital_publication_payload(
                request,
                publication,
                include_pdf=True,
            )
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_about_us(request):
    page = (
        AboutUsPage.objects
        .filter(is_published=True)
        .first()
    )

    if not page:
        return Response({"about": None})

    return Response(
        {
            "about": {
                "title": page.title,
                "subtitle": page.subtitle,
                "overview": page.overview,
                "history": page.history,
                "mission": page.mission,
                "vision": page.vision,
                "hero_image_url": (
                    _absolute_file_url(request, page.hero_image)
                    if page.hero_image
                    else ""
                ),
                "updated_at": page.updated_at.isoformat(),
            }
        }
    )


PEOPLE_GROUPS = [
    (
        "developers",
        PeopleProfile.Section.DEVELOPERS,
        "The Developers",
    ),
    (
        "capstone-committee",
        PeopleProfile.Section.CAPSTONE_COMMITTEE,
        "Capstone Committee",
    ),
    (
        "ics-faculty",
        PeopleProfile.Section.ICS_FACULTY,
        "ICS Faculty",
    ),
    (
        "equalizer-team",
        PeopleProfile.Section.EQUALIZER_TEAM,
        "The Equalizer Team",
    ),
]


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_people(request):
    groups = []

    for slug, section, title in PEOPLE_GROUPS:
        profiles = (
            PeopleProfile.objects
            .filter(
                section=section,
                is_active=True,
            )
            .order_by("display_order", "name")
        )

        groups.append(
            {
                "slug": slug,
                "title": title,
                "profiles": [
                    {
                        "id": profile.id,
                        "name": profile.name,
                        "image_url": _absolute_file_url(
                            request,
                            profile.image,
                        ),
                        "role_title": profile.role_title,
                        "courses_handled": profile.courses_handled,
                        "school_position": profile.school_position,
                        "institute_department": (
                            profile.institute_department
                        ),
                        "achievements": profile.achievements,
                        "additional_information": (
                            profile.additional_information
                        ),
                    }
                    for profile in profiles
                ],
            }
        )

    return Response({"groups": groups})
