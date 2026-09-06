from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from publications.models import (
    AboutUsPage,
    Article,
    Category,
    DigitalPublication,
    PeopleProfile,
    SchoolAdvertisement,
)


def _absolute_file_url(request, file_field):
    if not file_field:
        return ""

    try:
        url = file_field.url
    except (ValueError, AttributeError):
        return ""

    return request.build_absolute_uri(url)


def _published_articles():
    return (
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
            "attachments",
            "video_attachments",
            "contributors",
            "contributors__user",
        )
        .order_by(
            "-published_at",
            "-created_at",
        )
    )


def _author_payload(user):
    return {
        "username": user.username,
        "display_name": user.get_full_name().strip() or user.username,
    }


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
        "author": _author_payload(article.author),
        "published_at": (
            published_value.isoformat()
            if published_value
            else None
        ),
        "updated_at": article.updated_at.isoformat(),
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
                    "role": contributor.role,
                    "role_display": contributor.get_role_display(),
                }
                for contributor in article.contributors.all()
            ],
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
    search_query = request.GET.get("q", "").strip()[:100]

    if category_slug:
        articles = articles.filter(category__slug=category_slug)

    if search_query:
        articles = (
            articles
            .filter(
                Q(title__icontains=search_query)
                | Q(subtitle__icontains=search_query)
                | Q(excerpt__icontains=search_query)
                | Q(content__icontains=search_query)
                | Q(author__username__icontains=search_query)
                | Q(tags__name__icontains=search_query)
            )
            .distinct()
        )

    try:
        limit = int(request.GET.get("limit", "50"))
    except (TypeError, ValueError):
        limit = 50

    limit = max(1, min(limit, 100))
    articles = list(articles[:limit])

    return Response(
        {
            "count": len(articles),
            "articles": [
                _article_summary_payload(request, article)
                for article in articles
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def mobile_article_detail(request, slug):
    article = get_object_or_404(
        _published_articles(),
        slug=slug,
    )

    return Response(
        {
            "article": _article_detail_payload(request, article),
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
