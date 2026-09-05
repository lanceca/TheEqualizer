import io
import re
from html import escape, unescape

from django.contrib import messages
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.utils.html import strip_tags

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as PDFImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
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


# ==========================================================
# ARTICLE PDF HELPERS
# ==========================================================


def clean_pdf_text(value):
    """Return plain, XML-safe text for a ReportLab paragraph."""

    value = unescape(str(value or ""))
    value = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
        "",
        value,
    )
    return escape(value)


def article_content_paragraphs(content):
    """Convert stored plain text or basic HTML into PDF paragraphs."""

    content = str(content or "")
    content = re.sub(
        r"(?i)<br\s*/?>",
        "\n",
        content,
    )
    content = re.sub(
        r"(?i)</(?:p|div|h[1-6]|li|blockquote)>",
        "\n\n",
        content,
    )
    content = unescape(strip_tags(content))
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", content)
        if paragraph.strip()
    ]


def pdf_image_flowable(file_field, max_width, max_height):
    """Create a bounded PDF image, or return None if storage cannot read it."""

    if not file_field:
        return None

    try:
        file_field.open("rb")
        image_data = io.BytesIO(file_field.read())
        file_field.close()

        image = PDFImage(image_data)
        scale = min(
            max_width / image.imageWidth,
            max_height / image.imageHeight,
            1,
        )
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        image.hAlign = "CENTER"
        return image
    except Exception:
        try:
            file_field.close()
        except Exception:
            pass
        return None


def draw_article_pdf_page(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d7dfdb"))
    canvas.line(
        document.leftMargin,
        0.55 * inch,
        letter[0] - document.rightMargin,
        0.55 * inch,
    )
    canvas.setFillColor(colors.HexColor("#65736d"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        document.leftMargin,
        0.35 * inch,
        "The Equalizer",
    )
    canvas.drawRightString(
        letter[0] - document.rightMargin,
        0.35 * inch,
        f"Page {document.page}",
    )
    canvas.restoreState()


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

    published_articles = list(
        published_articles
    )

    lead_article = (
        published_articles[0]
        if published_articles
        else None
    )

    secondary_articles = (
        published_articles[1:5]
        if published_articles
        else []
    )

    more_articles = (
        published_articles[5:]
        if published_articles
        else []
    )

    homepage_advertisements = list(
        SchoolAdvertisement.objects
        .filter(
            is_active=True,
        )
        .order_by(
            "display_order",
            "-updated_at",
        )[:4]
    )

    return render(
        request,
        "home/home.html",
        {
            "published_articles": (
                published_articles
            ),
            "lead_article": (
                lead_article
            ),
            "secondary_articles": (
                secondary_articles
            ),
            "more_articles": (
                more_articles
            ),
            "homepage_advertisements": (
                homepage_advertisements
            ),
        },
    )




# ==========================================================
# PUBLIC CATEGORY ARTICLES
# ==========================================================


def category_articles(
    request,
    category_slug,
):
    category = get_object_or_404(
        Category,
        slug=category_slug,
    )

    category_search_query = (
        request.GET.get("q", "").strip()[:100]
    )

    articles = (
        Article.objects
        .filter(
            category=category,
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
    )

    if category_search_query:
        articles = (
            articles
            .filter(
                Q(
                    title__icontains=(
                        category_search_query
                    )
                )
                | Q(
                    subtitle__icontains=(
                        category_search_query
                    )
                )
                | Q(
                    excerpt__icontains=(
                        category_search_query
                    )
                )
                | Q(
                    content__icontains=(
                        category_search_query
                    )
                )
                | Q(
                    author__username__icontains=(
                        category_search_query
                    )
                )
                | Q(
                    tags__name__icontains=(
                        category_search_query
                    )
                )
            )
            .distinct()
        )

    articles = list(
        articles.order_by(
            "-published_at",
            "-created_at",
        )
    )

    lead_article = (
        articles[0]
        if articles
        else None
    )

    remaining_articles = (
        articles[1:]
        if articles
        else []
    )

    return render(
        request,
        "home/category_articles.html",
        {
            "category": category,
            "category_search_query": (
                category_search_query
            ),
            "articles": articles,
            "lead_article": lead_article,
            "remaining_articles": (
                remaining_articles
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
            "video_attachments",
            "contributors",
            "contributors__user",
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
# PUBLIC ARTICLE PDF DOWNLOAD
# ==========================================================


def download_article_pdf(
    request,
    slug,
):
    """Download the current published article as a branded PDF."""

    article = get_object_or_404(
        Article.objects
        .select_related(
            "category",
            "author",
        )
        .prefetch_related(
            "tags",
            "attachments",
            "contributors",
            "contributors__user",
        ),
        slug=slug,
        draft_type=Article.DraftType.NORMAL,
        is_published=True,
        is_archived=False,
    )

    pdf_buffer = io.BytesIO()
    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.75 * inch,
        title=article.title,
        author="The Equalizer",
        subject="Published article",
    )

    sample_styles = getSampleStyleSheet()
    styles = {
        "masthead": ParagraphStyle(
            "EqualizerMasthead",
            parent=sample_styles["Heading2"],
            fontName="Times-Bold",
            fontSize=19,
            leading=22,
            textColor=colors.HexColor("#173f32"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "category": ParagraphStyle(
            "EqualizerCategory",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#a37d0f"),
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "title": ParagraphStyle(
            "EqualizerTitle",
            parent=sample_styles["Title"],
            fontName="Times-Bold",
            fontSize=25,
            leading=29,
            textColor=colors.HexColor("#0e2a22"),
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "EqualizerSubtitle",
            parent=sample_styles["Normal"],
            fontName="Times-Italic",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#48534e"),
            spaceAfter=10,
        ),
        "metadata": ParagraphStyle(
            "EqualizerMetadata",
            parent=sample_styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#5f6d67"),
            spaceAfter=5,
        ),
        "excerpt": ParagraphStyle(
            "EqualizerExcerpt",
            parent=sample_styles["Normal"],
            fontName="Times-BoldItalic",
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#33463e"),
            leftIndent=12,
            rightIndent=12,
            spaceBefore=9,
            spaceAfter=13,
        ),
        "body": ParagraphStyle(
            "EqualizerBody",
            parent=sample_styles["BodyText"],
            fontName="Times-Roman",
            fontSize=11,
            leading=17,
            textColor=colors.HexColor("#1d2924"),
            alignment=4,
            spaceAfter=10,
        ),
        "caption": ParagraphStyle(
            "EqualizerCaption",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#65736d"),
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "tags": ParagraphStyle(
            "EqualizerTags",
            parent=sample_styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#65736d"),
            spaceBefore=10,
        ),
    }

    published_value = article.published_at or article.created_at
    published_text = timezone.localtime(
        published_value
    ).strftime("%B %d, %Y at %I:%M %p")

    story = [
        Paragraph("THE EQUALIZER", styles["masthead"]),
        Paragraph(
            clean_pdf_text(article.category.name).upper(),
            styles["category"],
        ),
        HRFlowable(
            width="100%",
            thickness=0.8,
            color=colors.HexColor("#c9a227"),
            spaceAfter=16,
        ),
        Paragraph(
            clean_pdf_text(article.title),
            styles["title"],
        ),
    ]

    if article.subtitle:
        story.append(
            Paragraph(
                clean_pdf_text(article.subtitle),
                styles["subtitle"],
            )
        )

    story.append(
        Paragraph(
            "By <b>"
            + clean_pdf_text(article.author.username)
            + "</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            + clean_pdf_text(published_text),
            styles["metadata"],
        )
    )

    contributor_lines = [
        (
            clean_pdf_text(contributor.user.username)
            + " ("
            + clean_pdf_text(contributor.get_role_display())
            + ")"
        )
        for contributor in article.contributors.all()
    ]
    if contributor_lines:
        story.append(
            Paragraph(
                "Contributors: " + ", ".join(contributor_lines),
                styles["metadata"],
            )
        )

    featured_image = pdf_image_flowable(
        article.featured_image,
        6.4 * inch,
        3.8 * inch,
    )
    if featured_image:
        story.extend(
            [
                Spacer(1, 9),
                featured_image,
                Spacer(1, 5),
            ]
        )

        featured_caption = article.featured_image_caption
        if article.featured_image_credit:
            featured_caption = (
                f"{featured_caption} — "
                if featured_caption
                else ""
            ) + f"Photo: {article.featured_image_credit}"
        if featured_caption:
            story.append(
                Paragraph(
                    clean_pdf_text(featured_caption),
                    styles["caption"],
                )
            )

    if article.excerpt:
        story.append(
            Paragraph(
                clean_pdf_text(article.excerpt),
                styles["excerpt"],
            )
        )

    paragraphs = article_content_paragraphs(
        article.content
    )
    for paragraph in paragraphs:
        story.append(
            Paragraph(
                clean_pdf_text(paragraph).replace("\n", "<br/>"),
                styles["body"],
            )
        )

    image_attachments = list(
        article.attachments.all()
    )
    if image_attachments:
        story.extend(
            [
                PageBreak(),
                Paragraph("Article Images", styles["title"]),
            ]
        )

        for attachment in image_attachments:
            attachment_image = pdf_image_flowable(
                attachment.image,
                6.4 * inch,
                4.8 * inch,
            )
            if not attachment_image:
                continue

            story.extend(
                [
                    attachment_image,
                    Spacer(1, 5),
                ]
            )

            caption = attachment.caption or attachment.alt_text
            if attachment.credit:
                caption = (
                    f"{caption} — " if caption else ""
                ) + f"Photo: {attachment.credit}"
            if caption:
                story.append(
                    Paragraph(
                        clean_pdf_text(caption),
                        styles["caption"],
                    )
                )
            story.append(Spacer(1, 10))

    tag_names = list(
        article.tags.values_list("name", flat=True)
    )
    if tag_names:
        story.append(
            Paragraph(
                "Tags: "
                + ", ".join(
                    clean_pdf_text(tag)
                    for tag in tag_names
                ),
                styles["tags"],
            )
        )

    document.build(
        story,
        onFirstPage=draw_article_pdf_page,
        onLaterPages=draw_article_pdf_page,
    )

    pdf_content = pdf_buffer.getvalue()

    response = HttpResponse(
        pdf_content,
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{article.slug}.pdf"'
    )
    response["Content-Length"] = str(
        len(pdf_content)
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


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

# ==========================================================
# PUBLIC DIGITAL PUBLICATIONS
# ==========================================================


def digital_publications(
    request,
):
    publications = (
        DigitalPublication.objects
        .filter(
            status=(
                DigitalPublication
                .Status
                .PUBLISHED
            )
        )
        .select_related(
            "uploaded_by"
        )
    )

    return render(
        request,
        "home/digital_publications.html",
        {
            "digital_publications": (
                publications
            ),
        },
    )


def digital_publication_detail(
    request,
    slug,
):
    publication = get_object_or_404(
        DigitalPublication,
        slug=slug,
        status=(
            DigitalPublication
            .Status
            .PUBLISHED
        ),
    )

    return render(
        request,
        (
            "home/"
            "digital_publication_detail.html"
        ),
        {
            "publication": publication,
        },
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def digital_publication_api(
    request,
    slug,
):
    publication = get_object_or_404(
        DigitalPublication,
        slug=slug,
        status=(
            DigitalPublication
            .Status
            .PUBLISHED
        ),
    )

    return Response(
        {
            "id": publication.id,
            "title": publication.title,
            "slug": publication.slug,
            "volume": publication.volume,
            "issue_number": (
                publication.issue_number
            ),
            "publication_date": (
                publication
                .publication_date
                .isoformat()
            ),
            "description": (
                publication.description
            ),
            "cover_image_url": (
                request.build_absolute_uri(
                    publication.cover_image.url
                )
                if publication.cover_image
                else ""
            ),
            "pdf_url": (
                request.build_absolute_uri(
                    publication.pdf_file.url
                )
            ),
            "page_count": (
                publication.page_count
            ),
            "file_size": (
                publication.file_size
            ),
        }
    )






# ==========================================================
# PEOPLE & TEAMS
# ==========================================================

PEOPLE_GROUP_DEFINITIONS = [
    (
        "developers",
        PeopleProfile.Section.DEVELOPERS,
        "The Developers",
        "Meet the developers behind The Equalizer CMS project.",
        "Build",
    ),
    (
        "capstone-committee",
        PeopleProfile.Section.CAPSTONE_COMMITTEE,
        "Capstone Committee",
        "Meet the Capstone Committee supporting the project.",
        "Guide",
    ),
    (
        "ics-faculty",
        PeopleProfile.Section.ICS_FACULTY,
        "ICS Faculty",
        "Meet the Institute of Computing Studies faculty.",
        "Teach",
    ),
    (
        "equalizer-team",
        PeopleProfile.Section.EQUALIZER_TEAM,
        "The Equalizer Team",
        "Meet the student publication team behind The Equalizer.",
        "Publish",
    ),
]


def people_and_teams(request):
    return render(
        request,
        "home/people_and_teams.html",
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def people_and_teams_api(request):
    groups = []

    for (
        slug,
        section,
        title,
        description,
        eyebrow,
    ) in PEOPLE_GROUP_DEFINITIONS:
        profiles = (
            PeopleProfile.objects
            .filter(
                section=section,
                is_active=True,
            )
            .order_by(
                "display_order",
                "name",
            )
        )

        groups.append({
            "slug": slug,
            "title": title,
            "description": description,
            "eyebrow": eyebrow,
            "profiles": [
                {
                    "id": profile.id,
                    "name": profile.name,
                    "image_url": (
                        request.build_absolute_uri(
                            profile.image.url
                        )
                        if profile.image
                        else ""
                    ),
                    "role_title": profile.role_title,
                    "school_position": profile.school_position,
                    "institute_department": profile.institute_department,
                    "courses_handled": profile.courses_handled,
                    "achievements": profile.achievements,
                    "additional_information": profile.additional_information,
                }
                for profile in profiles
            ],
        })

    return Response({"groups": groups})


# ==========================================================
# ABOUT US
# ==========================================================


def about_us(request):
    about_page = (
        AboutUsPage.objects
        .filter(
            is_published=True,
        )
        .select_related(
            "updated_by",
        )
        .first()
    )

    return render(
        request,
        "home/about_us.html",
        {
            "about_page": about_page,
        },
    )


# ==========================================================
# SCHOOL UPDATES / PUBLIC ADVERTISEMENT DETAILS
# ==========================================================


def school_updates(request):
    advertisements = (
        SchoolAdvertisement.objects
        .filter(
            is_active=True,
        )
        .order_by(
            "display_order",
            "-updated_at",
        )
    )

    return render(
        request,
        "home/school_updates.html",
        {
            "advertisements": advertisements,
        },
    )


def school_advertisement_detail(
    request,
    slug,
):
    advertisement = get_object_or_404(
        SchoolAdvertisement,
        slug=slug,
        is_active=True,
    )

    return render(
        request,
        "home/school_advertisement_detail.html",
        {
            "advertisement": advertisement,
        },
    )

