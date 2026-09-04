import io
from datetime import timedelta
from functools import wraps
from html import escape

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from analytics.models import ArticleDailyAnalytics

from publications.models import (
    Article,
    ContentReport,
    DeletionRequest,
    EditRequest,
    Submission,
)

from .forms import (
    AdminAccountCreationForm,
    AdminAccountEditForm,
    ProfileForm,
    StaffAccountCreationForm,
    StaffAccountEditForm,
    UsernameChangeForm,
)


User = get_user_model()


# ==========================================================
# ROLE PERMISSION HELPER
# ==========================================================


def role_required(*allowed_roles):
    """
    Restrict a view to users with one of the specified roles
    and prevent protected pages from being cached.
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
# DASHBOARD REDIRECT
# ==========================================================


@never_cache
@login_required
def dashboard_redirect(request):

    role = request.user.role

    if role == User.Role.SUPER_ADMIN:
        return redirect(
            "super_admin_dashboard"
        )

    elif role == User.Role.ADMIN:
        return redirect(
            "admin_dashboard"
        )

    elif role == User.Role.ADVISER:
        return redirect(
            "adviser_dashboard"
        )

    elif role == User.Role.EIC:
        return redirect(
            "eic_dashboard"
        )

    elif role == User.Role.EDITOR:
        return redirect(
            "editor_dashboard"
        )

    elif role == User.Role.STAFF:
        return redirect(
            "staff_dashboard"
        )

    return HttpResponseForbidden(
        "Your account does not have a valid role."
    )


# ==========================================================
# DASHBOARDS
# ==========================================================


@role_required(User.Role.SUPER_ADMIN)
def super_admin_dashboard(request):

    return render(
        request,
        "accounts/dashboards/super_admin.html",
    )


@role_required(User.Role.ADMIN)
def admin_dashboard(request):

    return render(
        request,
        "accounts/dashboards/admin.html",
    )


# ==========================================================
# ADVISER ANALYTICS DASHBOARD
# ==========================================================


@role_required(User.Role.ADVISER)
def adviser_dashboard(request):

    # ======================================================
    # BASE QUERYSETS
    # ======================================================

    normal_articles = Article.objects.filter(
        draft_type=Article.DraftType.NORMAL
    )

    published_queryset = normal_articles.filter(
        is_published=True,
        is_archived=False,
    )

    # ======================================================
    # ARTICLE / PUBLICATION TOTALS
    # ======================================================

    total_articles = normal_articles.count()

    published_articles = (
        published_queryset.count()
    )

    archived_articles = (
        normal_articles.filter(
            is_archived=True,
        ).count()
    )

    draft_articles = (
        normal_articles.filter(
            is_published=False,
            is_archived=False,
            submissions__isnull=True,
        )
        .distinct()
        .count()
    )

    # ======================================================
    # SUBMISSION TOTALS
    # ======================================================

    total_submissions = (
        Submission.objects.count()
    )

    pending_submissions = (
        Submission.objects.filter(
            status=Submission.Status.PENDING
        ).count()
    )

    approved_submissions = (
        Submission.objects.filter(
            status=Submission.Status.APPROVED
        ).count()
    )

    rejected_submissions = (
        Submission.objects.filter(
            status=Submission.Status.REJECTED
        ).count()
    )

    revision_submissions = (
        Submission.objects.filter(
            status=Submission.Status.REVISION
        ).count()
    )

    # ======================================================
    # EDIT REQUEST ANALYTICS
    # ======================================================

    pending_edit_requests = (
        EditRequest.objects.filter(
            status=EditRequest.Status.PENDING
        ).count()
    )

    approved_edit_requests = (
        EditRequest.objects.filter(
            status=EditRequest.Status.APPROVED
        ).count()
    )

    rejected_edit_requests = (
        EditRequest.objects.filter(
            status=EditRequest.Status.REJECTED
        ).count()
    )

    completed_edit_requests = (
        EditRequest.objects.filter(
            status=EditRequest.Status.COMPLETED
        ).count()
    )

    # ======================================================
    # DELETION REQUEST ANALYTICS
    # ======================================================

    pending_deletion_requests = (
        DeletionRequest.objects.filter(
            status=DeletionRequest.Status.PENDING
        ).count()
    )

    approved_deletion_requests = (
        DeletionRequest.objects.filter(
            status=DeletionRequest.Status.APPROVED
        ).count()
    )

    rejected_deletion_requests = (
        DeletionRequest.objects.filter(
            status=DeletionRequest.Status.REJECTED
        ).count()
    )

    # ======================================================
    # CONTENT REPORT ANALYTICS
    # ======================================================

    open_content_reports = (
        ContentReport.objects.filter(
            status=ContentReport.Status.OPEN
        ).count()
    )

    revision_required_reports = (
        ContentReport.objects.filter(
            status=ContentReport.Status.REVISION_REQUIRED
        ).count()
    )

    cancelled_content_reports = (
        ContentReport.objects.filter(
            status=ContentReport.Status.CANCELLED
        ).count()
    )

    resolved_content_reports = (
        ContentReport.objects.filter(
            status=ContentReport.Status.RESOLVED
        ).count()
    )

    active_content_reports = (
        open_content_reports
        + revision_required_reports
    )

    total_content_reports = (
        ContentReport.objects.count()
    )

    # ======================================================
    # READER ENGAGEMENT TOTALS
    # ======================================================

    reader_totals = (
        published_queryset.aggregate(
            total_views=Sum(
                "view_count"
            ),
            total_reactions=Sum(
                "reaction_count"
            ),
            total_shares=Sum(
                "share_count"
            ),
        )
    )

    total_views = (
        reader_totals["total_views"]
        or 0
    )

    total_reactions = (
        reader_totals["total_reactions"]
        or 0
    )

    total_shares = (
        reader_totals["total_shares"]
        or 0
    )

    total_engagement = (
        total_views
        + total_reactions
        + total_shares
    )

    # ======================================================
    # HISTORICAL READER ENGAGEMENT - LAST 30 MANILA DAYS
    # ======================================================

    analytics_end_date = timezone.localdate()
    analytics_start_date = (
        analytics_end_date
        - timedelta(days=29)
    )

    daily_engagement_rows = (
        ArticleDailyAnalytics.objects
        .filter(
            article__draft_type=Article.DraftType.NORMAL,
            date__range=(
                analytics_start_date,
                analytics_end_date,
            ),
        )
        .values("date")
        .annotate(
            views=Sum("views"),
            reactions=Sum("reactions"),
            shares=Sum("shares"),
        )
        .order_by("date")
    )

    daily_engagement_by_date = {
        row["date"]: {
            "views": row["views"] or 0,
            "reactions": row["reactions"] or 0,
            "shares": row["shares"] or 0,
        }
        for row in daily_engagement_rows
    }

    historical_engagement_labels = []
    historical_engagement_full_dates = []
    historical_views = []
    historical_reactions = []
    historical_shares = []

    for day_offset in range(30):

        current_date = (
            analytics_start_date
            + timedelta(days=day_offset)
        )

        current_values = (
            daily_engagement_by_date.get(
                current_date,
                {
                    "views": 0,
                    "reactions": 0,
                    "shares": 0,
                },
            )
        )

        historical_engagement_labels.append(
            current_date.strftime("%b %d")
        )

        historical_engagement_full_dates.append(
            current_date.isoformat()
        )

        historical_views.append(
            current_values["views"]
        )

        historical_reactions.append(
            current_values["reactions"]
        )

        historical_shares.append(
            current_values["shares"]
        )

    thirty_day_views = sum(
        historical_views
    )

    thirty_day_reactions = sum(
        historical_reactions
    )

    thirty_day_shares = sum(
        historical_shares
    )

    thirty_day_engagement = (
        thirty_day_views
        + thirty_day_reactions
        + thirty_day_shares
    )

    # ======================================================
    # EDITOR PERFORMANCE
    # ======================================================

    editors = (
        User.objects
        .filter(
            role=User.Role.EDITOR
        )
        .annotate(
            article_count=Count(
                "articles",
                filter=Q(
                    articles__draft_type=(
                        Article.DraftType.NORMAL
                    )
                ),
                distinct=True,
            ),

            published_count=Count(
                "articles",
                filter=Q(
                    articles__draft_type=(
                        Article.DraftType.NORMAL
                    ),
                    articles__is_published=True,
                    articles__is_archived=False,
                ),
                distinct=True,
            ),

            archived_count=Count(
                "articles",
                filter=Q(
                    articles__draft_type=(
                        Article.DraftType.NORMAL
                    ),
                    articles__is_archived=True,
                ),
                distinct=True,
            ),

            submission_count=Count(
                "submissions",
                distinct=True,
            ),

            pending_count=Count(
                "submissions",
                filter=Q(
                    submissions__status=(
                        Submission.Status.PENDING
                    )
                ),
                distinct=True,
            ),

            approved_count=Count(
                "submissions",
                filter=Q(
                    submissions__status=(
                        Submission.Status.APPROVED
                    )
                ),
                distinct=True,
            ),

            rejected_count=Count(
                "submissions",
                filter=Q(
                    submissions__status=(
                        Submission.Status.REJECTED
                    )
                ),
                distinct=True,
            ),

            revision_count=Count(
                "submissions",
                filter=Q(
                    submissions__status=(
                        Submission.Status.REVISION
                    )
                ),
                distinct=True,
            ),
        )
        .order_by(
            "-published_count",
            "-approved_count",
            "username",
        )
    )

    # ======================================================
    # CATEGORY PERFORMANCE
    # ======================================================

    category_performance = (
        published_queryset
        .values(
            "category__name"
        )
        .annotate(
            article_count=Count(
                "id",
                distinct=True,
            ),
            total_views=Sum(
                "view_count"
            ),
            total_reactions=Sum(
                "reaction_count"
            ),
            total_shares=Sum(
                "share_count"
            ),
        )
        .order_by(
            "-total_views",
            "-article_count",
            "category__name",
        )
    )

    # ======================================================
    # TOP ARTICLES
    # ======================================================

    top_viewed_articles = (
        published_queryset
        .select_related(
            "category",
            "author",
        )
        .order_by(
            "-view_count",
            "-published_at",
        )[:5]
    )

    top_reacted_articles = (
        published_queryset
        .select_related(
            "category",
            "author",
        )
        .order_by(
            "-reaction_count",
            "-published_at",
        )[:5]
    )

    top_shared_articles = (
        published_queryset
        .select_related(
            "category",
            "author",
        )
        .order_by(
            "-share_count",
            "-published_at",
        )[:5]
    )

    # ======================================================
    # CHART-READY DATA
    # ======================================================

    article_status_chart_data = [
        {
            "label": "Published",
            "value": published_articles,
        },
        {
            "label": "Draft",
            "value": draft_articles,
        },
        {
            "label": "Archived",
            "value": archived_articles,
        },
    ]

    submission_chart_data = [
        {
            "label": "Pending",
            "value": pending_submissions,
        },
        {
            "label": "Approved",
            "value": approved_submissions,
        },
        {
            "label": "Rejected",
            "value": rejected_submissions,
        },
        {
            "label": "Revision",
            "value": revision_submissions,
        },
    ]

    edit_request_chart_data = [
        {
            "label": "Pending",
            "value": pending_edit_requests,
        },
        {
            "label": "Approved",
            "value": approved_edit_requests,
        },
        {
            "label": "Rejected",
            "value": rejected_edit_requests,
        },
        {
            "label": "Completed",
            "value": completed_edit_requests,
        },
    ]

    deletion_request_chart_data = [
        {
            "label": "Pending",
            "value": pending_deletion_requests,
        },
        {
            "label": "Approved",
            "value": approved_deletion_requests,
        },
        {
            "label": "Rejected",
            "value": rejected_deletion_requests,
        },
    ]

    content_report_chart_data = [
        {
            "label": "Open",
            "value": open_content_reports,
        },
        {
            "label": "Revision Required",
            "value": revision_required_reports,
        },
        {
            "label": "Resolved",
            "value": resolved_content_reports,
        },
        {
            "label": "Cancelled",
            "value": cancelled_content_reports,
        },
    ]

    reader_engagement_chart_data = [
        {
            "label": "Views",
            "value": total_views,
        },
        {
            "label": "Reactions",
            "value": total_reactions,
        },
        {
            "label": "Shares",
            "value": total_shares,
        },
    ]

    category_chart_data = [
        {
            "label": (
                category["category__name"]
            ),
            "articles": (
                category["article_count"]
            ),
            "views": (
                category["total_views"]
                or 0
            ),
            "reactions": (
                category["total_reactions"]
                or 0
            ),
            "shares": (
                category["total_shares"]
                or 0
            ),
        }
        for category in category_performance
    ]

    editor_chart_data = [
        {
            "username": editor.username,
            "articles": editor.article_count,
            "published": editor.published_count,
            "archived": editor.archived_count,
            "submissions": editor.submission_count,
            "pending": editor.pending_count,
            "approved": editor.approved_count,
            "rejected": editor.rejected_count,
            "revision": editor.revision_count,
        }
        for editor in editors
    ]

    # ======================================================
    # CONTEXT
    # ======================================================

    context = {
        "total_articles": total_articles,
        "published_articles": published_articles,
        "archived_articles": archived_articles,
        "draft_articles": draft_articles,

        "total_submissions": total_submissions,
        "pending_submissions": pending_submissions,
        "approved_submissions": approved_submissions,
        "rejected_submissions": rejected_submissions,
        "revision_submissions": revision_submissions,

        "pending_edit_requests": pending_edit_requests,
        "approved_edit_requests": approved_edit_requests,
        "rejected_edit_requests": rejected_edit_requests,
        "completed_edit_requests": completed_edit_requests,

        "pending_deletion_requests": (
            pending_deletion_requests
        ),
        "approved_deletion_requests": (
            approved_deletion_requests
        ),
        "rejected_deletion_requests": (
            rejected_deletion_requests
        ),

        "total_content_reports": (
            total_content_reports
        ),
        "open_content_reports": (
            open_content_reports
        ),
        "revision_required_reports": (
            revision_required_reports
        ),
        "cancelled_content_reports": (
            cancelled_content_reports
        ),
        "active_content_reports": (
            active_content_reports
        ),
        "resolved_content_reports": (
            resolved_content_reports
        ),

        "total_views": total_views,
        "total_reactions": total_reactions,
        "total_shares": total_shares,
        "total_engagement": total_engagement,

        "analytics_start_date": analytics_start_date,
        "analytics_end_date": analytics_end_date,
        "thirty_day_views": thirty_day_views,
        "thirty_day_reactions": thirty_day_reactions,
        "thirty_day_shares": thirty_day_shares,
        "thirty_day_engagement": thirty_day_engagement,
        "historical_engagement_labels": (
            historical_engagement_labels
        ),
        "historical_engagement_full_dates": (
            historical_engagement_full_dates
        ),
        "historical_views": historical_views,
        "historical_reactions": historical_reactions,
        "historical_shares": historical_shares,

        "editors": editors,
        "category_performance": (
            category_performance
        ),

        "top_viewed_articles": (
            top_viewed_articles
        ),
        "top_reacted_articles": (
            top_reacted_articles
        ),
        "top_shared_articles": (
            top_shared_articles
        ),

        "article_status_chart_data": (
            article_status_chart_data
        ),
        "submission_chart_data": (
            submission_chart_data
        ),
        "edit_request_chart_data": (
            edit_request_chart_data
        ),
        "deletion_request_chart_data": (
            deletion_request_chart_data
        ),
        "content_report_chart_data": (
            content_report_chart_data
        ),
        "reader_engagement_chart_data": (
            reader_engagement_chart_data
        ),
        "category_chart_data": (
            category_chart_data
        ),
        "editor_chart_data": (
            editor_chart_data
        ),
    }

    return render(
        request,
        "accounts/dashboards/adviser.html",
        context,
    )


def draw_adviser_report_page(canvas, document):
    """Draw a consistent header and footer on analytics report pages."""

    page_width, page_height = landscape(letter)

    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#173f32"))
    canvas.rect(
        0,
        page_height - 0.46 * inch,
        page_width,
        0.46 * inch,
        fill=1,
        stroke=0,
    )
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(
        document.leftMargin,
        page_height - 0.3 * inch,
        "THE EQUALIZER — ADVISER ANALYTICS",
    )
    canvas.setStrokeColor(colors.HexColor("#d7dfdb"))
    canvas.line(
        document.leftMargin,
        0.48 * inch,
        page_width - document.rightMargin,
        0.48 * inch,
    )
    canvas.setFillColor(colors.HexColor("#65736d"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        document.leftMargin,
        0.28 * inch,
        f"Generated {timezone.localtime().strftime('%B %d, %Y %I:%M %p')}",
    )
    canvas.drawRightString(
        page_width - document.rightMargin,
        0.28 * inch,
        f"Page {document.page}",
    )
    canvas.restoreState()


@role_required(User.Role.ADVISER)
def download_adviser_analytics_pdf(request):
    """Download a printable snapshot of the Adviser analytics dashboard."""

    normal_articles = Article.objects.filter(
        draft_type=Article.DraftType.NORMAL
    )
    published_queryset = normal_articles.filter(
        is_published=True,
        is_archived=False,
    )

    total_articles = normal_articles.count()
    published_articles = published_queryset.count()
    archived_articles = normal_articles.filter(
        is_archived=True
    ).count()
    draft_articles = (
        normal_articles
        .filter(
            is_published=False,
            is_archived=False,
            submissions__isnull=True,
        )
        .distinct()
        .count()
    )

    reader_totals = published_queryset.aggregate(
        total_views=Sum("view_count"),
        total_reactions=Sum("reaction_count"),
        total_shares=Sum("share_count"),
    )
    total_views = reader_totals["total_views"] or 0
    total_reactions = reader_totals["total_reactions"] or 0
    total_shares = reader_totals["total_shares"] or 0

    report_end_date = timezone.localdate()
    report_start_date = report_end_date - timedelta(days=29)
    thirty_day_totals = (
        ArticleDailyAnalytics.objects
        .filter(
            article__draft_type=Article.DraftType.NORMAL,
            date__range=(report_start_date, report_end_date),
        )
        .aggregate(
            views=Sum("views"),
            reactions=Sum("reactions"),
            shares=Sum("shares"),
        )
    )

    submission_counts = {
        status: Submission.objects.filter(status=status).count()
        for status in [
            Submission.Status.PENDING,
            Submission.Status.APPROVED,
            Submission.Status.REJECTED,
            Submission.Status.REVISION,
        ]
    }
    edit_request_counts = {
        status: EditRequest.objects.filter(status=status).count()
        for status in [
            EditRequest.Status.PENDING,
            EditRequest.Status.APPROVED,
            EditRequest.Status.REJECTED,
            EditRequest.Status.COMPLETED,
        ]
    }
    deletion_request_counts = {
        status: DeletionRequest.objects.filter(status=status).count()
        for status in [
            DeletionRequest.Status.PENDING,
            DeletionRequest.Status.APPROVED,
            DeletionRequest.Status.REJECTED,
        ]
    }
    content_report_counts = {
        status: ContentReport.objects.filter(status=status).count()
        for status in [
            ContentReport.Status.OPEN,
            ContentReport.Status.REVISION_REQUIRED,
            ContentReport.Status.RESOLVED,
            ContentReport.Status.CANCELLED,
        ]
    }

    category_performance = list(
        published_queryset
        .values("category__name")
        .annotate(
            article_count=Count("id", distinct=True),
            total_views=Sum("view_count"),
            total_reactions=Sum("reaction_count"),
            total_shares=Sum("share_count"),
        )
        .order_by("-total_views", "category__name")
    )

    editors = list(
        User.objects
        .filter(role=User.Role.EDITOR)
        .annotate(
            article_count=Count(
                "articles",
                filter=Q(
                    articles__draft_type=Article.DraftType.NORMAL
                ),
                distinct=True,
            ),
            published_count=Count(
                "articles",
                filter=Q(
                    articles__draft_type=Article.DraftType.NORMAL,
                    articles__is_published=True,
                    articles__is_archived=False,
                ),
                distinct=True,
            ),
            approved_count=Count(
                "submissions",
                filter=Q(
                    submissions__status=Submission.Status.APPROVED
                ),
                distinct=True,
            ),
            revision_count=Count(
                "submissions",
                filter=Q(
                    submissions__status=Submission.Status.REVISION
                ),
                distinct=True,
            ),
        )
        .order_by("-published_count", "username")
    )

    top_articles = list(
        published_queryset
        .select_related("category", "author")
        .order_by("-view_count", "-reaction_count", "-share_count")[:10]
    )

    pdf_buffer = io.BytesIO()
    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.66 * inch,
        bottomMargin=0.65 * inch,
        title="The Equalizer Adviser Analytics",
        author=request.user.username,
        subject="Publication analytics report",
    )

    sample_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AnalyticsTitle",
        parent=sample_styles["Title"],
        fontName="Times-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0e2a22"),
        alignment=TA_CENTER,
        spaceAfter=5,
    )
    subtitle_style = ParagraphStyle(
        "AnalyticsSubtitle",
        parent=sample_styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#65736d"),
        alignment=TA_CENTER,
        spaceAfter=15,
    )
    heading_style = ParagraphStyle(
        "AnalyticsHeading",
        parent=sample_styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#173f32"),
        spaceBefore=8,
        spaceAfter=7,
    )
    cell_style = ParagraphStyle(
        "AnalyticsCell",
        parent=sample_styles["Normal"],
        fontSize=7.5,
        leading=10,
    )

    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173f32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cad5cf")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f5")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )

    def report_table(rows, widths=None, repeat_rows=1):
        table_class = LongTable if len(rows) > 12 else Table
        table = table_class(
            rows,
            colWidths=widths,
            repeatRows=repeat_rows,
            hAlign="LEFT",
        )
        table.setStyle(table_style)
        return table

    story = [
        Paragraph("Adviser Analytics Report", title_style),
        Paragraph(
            f"Reporting snapshot through {report_end_date.strftime('%B %d, %Y')} "
            f"(Asia/Manila) · Prepared for {escape(request.user.username)}",
            subtitle_style,
        ),
        Paragraph("Publication and engagement overview", heading_style),
        report_table(
            [
                ["Articles", "Published", "Draft", "Archived", "Views", "Reactions", "Shares"],
                [
                    total_articles,
                    published_articles,
                    draft_articles,
                    archived_articles,
                    total_views,
                    total_reactions,
                    total_shares,
                ],
            ],
            [1.15 * inch] * 7,
        ),
        Spacer(1, 10),
        Paragraph("Last 30 days", heading_style),
        report_table(
            [
                ["Date range", "Views", "Reactions", "Shares", "Total engagement"],
                [
                    f"{report_start_date:%b %d, %Y} – {report_end_date:%b %d, %Y}",
                    thirty_day_totals["views"] or 0,
                    thirty_day_totals["reactions"] or 0,
                    thirty_day_totals["shares"] or 0,
                    (thirty_day_totals["views"] or 0)
                    + (thirty_day_totals["reactions"] or 0)
                    + (thirty_day_totals["shares"] or 0),
                ],
            ],
            [2.4 * inch, 1.35 * inch, 1.35 * inch, 1.35 * inch, 1.55 * inch],
        ),
        Spacer(1, 10),
        Paragraph("Editorial workflow", heading_style),
        report_table(
            [
                ["Workflow", "Pending/Open", "Approved/Resolved", "Rejected/Cancelled", "Revision/Completed"],
                [
                    "Submissions",
                    submission_counts[Submission.Status.PENDING],
                    submission_counts[Submission.Status.APPROVED],
                    submission_counts[Submission.Status.REJECTED],
                    submission_counts[Submission.Status.REVISION],
                ],
                [
                    "Edit requests",
                    edit_request_counts[EditRequest.Status.PENDING],
                    edit_request_counts[EditRequest.Status.APPROVED],
                    edit_request_counts[EditRequest.Status.REJECTED],
                    edit_request_counts[EditRequest.Status.COMPLETED],
                ],
                [
                    "Deletion requests",
                    deletion_request_counts[DeletionRequest.Status.PENDING],
                    deletion_request_counts[DeletionRequest.Status.APPROVED],
                    deletion_request_counts[DeletionRequest.Status.REJECTED],
                    "—",
                ],
                [
                    "Content reports",
                    content_report_counts[ContentReport.Status.OPEN],
                    content_report_counts[ContentReport.Status.RESOLVED],
                    content_report_counts[ContentReport.Status.CANCELLED],
                    content_report_counts[ContentReport.Status.REVISION_REQUIRED],
                ],
            ],
            [1.55 * inch, 1.55 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch],
        ),
        PageBreak(),
        Paragraph("Category performance", heading_style),
        report_table(
            [["Category", "Published articles", "Views", "Reactions", "Shares"]]
            + [
                [
                    Paragraph(escape(row["category__name"] or "Uncategorized"), cell_style),
                    row["article_count"],
                    row["total_views"] or 0,
                    row["total_reactions"] or 0,
                    row["total_shares"] or 0,
                ]
                for row in category_performance
            ],
            [2.7 * inch, 1.45 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
        ),
        Spacer(1, 12),
        Paragraph("Editor performance", heading_style),
        report_table(
            [["Editor", "Articles", "Published", "Approved submissions", "Revision submissions"]]
            + [
                [
                    Paragraph(escape(editor.username), cell_style),
                    editor.article_count,
                    editor.published_count,
                    editor.approved_count,
                    editor.revision_count,
                ]
                for editor in editors
            ],
            [2.7 * inch, 1.2 * inch, 1.2 * inch, 1.6 * inch, 1.6 * inch],
        ),
        PageBreak(),
        Paragraph("Top published articles", heading_style),
        report_table(
            [["Article", "Category", "Author", "Views", "Reactions", "Shares"]]
            + [
                [
                    Paragraph(escape(article.title), cell_style),
                    Paragraph(escape(article.category.name), cell_style),
                    Paragraph(escape(article.author.username), cell_style),
                    article.view_count,
                    article.reaction_count,
                    article.share_count,
                ]
                for article in top_articles
            ],
            [3.2 * inch, 1.45 * inch, 1.35 * inch, 0.8 * inch, 0.9 * inch, 0.8 * inch],
        ),
    ]

    document.build(
        story,
        onFirstPage=draw_adviser_report_page,
        onLaterPages=draw_adviser_report_page,
    )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        "attachment; filename=the-equalizer-adviser-analytics-"
        f"{report_end_date.isoformat()}.pdf"
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response

@role_required(User.Role.EIC)
def eic_dashboard(request):

    return render(
        request,
        "accounts/dashboards/eic.html",
    )


@role_required(User.Role.EDITOR)
def editor_dashboard(request):

    return render(
        request,
        "accounts/dashboards/editor.html",
    )


@role_required(User.Role.STAFF)
def staff_dashboard(request):

    return render(
        request,
        "accounts/dashboards/staff.html",
    )


# ==========================================================
# LOGIN / LOGOUT
# ==========================================================


@never_cache
def login_view(request):

    if request.user.is_authenticated:
        return redirect(
            "dashboard"
        )

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:

            login(
                request,
                user,
            )

            messages.success(
                request,
                f"Welcome back, {user.username}.",
            )

            return redirect(
                "dashboard"
            )

        messages.error(
            request,
            "Invalid username or password.",
        )

        return render(
            request,
            "accounts/login.html",
        )

    return render(
        request,
        "accounts/login.html",
    )


@require_POST
@never_cache
def logout_view(request):

    if request.user.is_authenticated:

        username = request.user.username

        logout(
            request
        )

        messages.info(
            request,
            f"{username} has been logged out.",
        )

    return redirect(
        "login"
    )


# ==========================================================
# PROFILE MANAGEMENT
# ==========================================================


@never_cache
@login_required
def profile(request):

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            instance=request.user,
        )

        uploaded_profile_picture = (
            request.FILES.get(
                "profile_picture"
            )
        )

        remove_profile_picture = (
            request.POST.get(
                "remove_profile_picture"
            )
            == "1"
        )

        if form.is_valid():

            user = form.save(
                commit=False
            )

            old_profile_picture_name = (
                request.user.profile_picture.name
                if request.user.profile_picture
                else ""
            )

            if remove_profile_picture:
                user.profile_picture = None

            elif uploaded_profile_picture:
                user.profile_picture = (
                    uploaded_profile_picture
                )

            try:

                user.full_clean()

            except ValidationError as error:

                for message in error.messages:
                    messages.error(
                        request,
                        message,
                    )

            else:

                user.save()
                form.save_m2m()

                new_profile_picture_name = (
                    user.profile_picture.name
                    if user.profile_picture
                    else ""
                )

                if (
                    old_profile_picture_name
                    and old_profile_picture_name
                    != new_profile_picture_name
                ):
                    default_storage.delete(
                        old_profile_picture_name
                    )

                messages.success(
                    request,
                    (
                        "Your profile was updated "
                        "successfully."
                    ),
                )

                return redirect(
                    "profile"
                )

        else:

            messages.error(
                request,
                (
                    "Your profile could not be updated. "
                    "Please check the form."
                ),
            )

    else:

        form = ProfileForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
        },
    )


@never_cache
@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST,
        )

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user,
            )

            messages.success(
                request,
                "Your password was changed successfully.",
            )

            return redirect(
                "profile"
            )

        messages.error(
            request,
            "Your password could not be changed. Please check the form.",
        )

    else:

        form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "accounts/change_password.html",
        {
            "form": form,
        },
    )


# ==========================================================
# SELF-SERVICE USERNAME CHANGE
# ==========================================================


@never_cache
@login_required
def change_username(request):

    old_username = request.user.username

    if request.method == "POST":

        form = UsernameChangeForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            user = form.save()

            messages.success(
                request,
                (
                    f'Your login username was changed '
                    f'from "{old_username}" to '
                    f'"{user.username}".'
                ),
            )

            return redirect(
                "profile"
            )

        messages.error(
            request,
            (
                "Your username could not be changed. "
                "Please check the form."
            ),
        )

    else:

        form = UsernameChangeForm(
            user=request.user
        )

    return render(
        request,
        "accounts/change_username.html",
        {
            "form": form,
        },
    )


# ==========================================================
# ADVISER / EIC - STAFF DIRECTORY
# ==========================================================


@role_required(
    User.Role.ADVISER,
    User.Role.EIC,
)
def staff_directory(request):

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    selected_role = request.GET.get(
        "role",
        "ALL",
    )

    directory_roles = [
        User.Role.EIC,
        User.Role.EDITOR,
        User.Role.STAFF,
    ]

    staff_accounts = (
        User.objects
        .filter(
            role__in=directory_roles,
            is_active=True,
        )
    )

    if selected_role in directory_roles:

        staff_accounts = (
            staff_accounts.filter(
                role=selected_role
            )
        )

    if search_query:

        staff_accounts = (
            staff_accounts.filter(
                Q(
                    username__icontains=search_query
                )
                | Q(
                    first_name__icontains=search_query
                )
                | Q(
                    last_name__icontains=search_query
                )
                | Q(
                    email__icontains=search_query
                )
            )
        )

    role_order = {
        User.Role.EIC: 0,
        User.Role.EDITOR: 1,
        User.Role.STAFF: 2,
    }

    staff_accounts = sorted(
        staff_accounts,
        key=lambda user: (
            role_order.get(
                user.role,
                99,
            ),
            user.username.lower(),
        ),
    )

    return render(
        request,
        "accounts/staff_directory.html",
        {
            "staff_accounts": (
                staff_accounts
            ),
            "search_query": search_query,
            "selected_role": selected_role,
            "role_choices": [
                (
                    User.Role.EIC,
                    User.Role.EIC.label,
                ),
                (
                    User.Role.EDITOR,
                    User.Role.EDITOR.label,
                ),
                (
                    User.Role.STAFF,
                    User.Role.STAFF.label,
                ),
            ],
        },
    )


# ==========================================================
# SUPER ADMIN - MANAGE ADMIN ACCOUNTS
# ==========================================================


@role_required(User.Role.SUPER_ADMIN)
def manage_admin_accounts(request):

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    admins = User.objects.filter(
        role=User.Role.ADMIN
    )

    if search_query:

        admins = admins.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    admins = admins.order_by(
        "username"
    )

    return render(
        request,
        "accounts/manage_admins.html",
        {
            "admins": admins,
            "search_query": search_query,
        },
    )


@role_required(User.Role.SUPER_ADMIN)
def create_admin_account(request):

    if request.method == "POST":

        form = AdminAccountCreationForm(
            request.POST
        )

        if form.is_valid():

            admin_user = form.save()

            messages.success(
                request,
                (
                    f'Admin account "{admin_user.username}" '
                    f"was created successfully."
                ),
            )

            return redirect(
                "manage_admin_accounts"
            )

        messages.error(
            request,
            "The Admin account could not be created. Please check the form.",
        )

    else:

        form = AdminAccountCreationForm()

    return render(
        request,
        "accounts/create_admin_account.html",
        {
            "form": form,
        },
    )


@role_required(User.Role.SUPER_ADMIN)
def edit_admin_account(
    request,
    user_id,
):

    admin_user = get_object_or_404(
        User,
        id=user_id,
        role=User.Role.ADMIN,
    )

    if request.method == "POST":

        form = AdminAccountEditForm(
            request.POST,
            instance=admin_user,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                (
                    f'Admin account "{admin_user.username}" '
                    f"was updated successfully."
                ),
            )

            return redirect(
                "manage_admin_accounts"
            )

        messages.error(
            request,
            "The Admin account could not be updated. Please check the form.",
        )

    else:

        form = AdminAccountEditForm(
            instance=admin_user
        )

    return render(
        request,
        "accounts/edit_admin_account.html",
        {
            "form": form,
            "managed_user": admin_user,
        },
    )


@role_required(User.Role.SUPER_ADMIN)
def toggle_admin_account_status(
    request,
    user_id,
):

    if request.method != "POST":

        return redirect(
            "manage_admin_accounts"
        )

    admin_user = get_object_or_404(
        User,
        id=user_id,
        role=User.Role.ADMIN,
    )

    admin_user.is_active = (
        not admin_user.is_active
    )

    admin_user.save(
        update_fields=[
            "is_active",
        ]
    )

    if admin_user.is_active:

        messages.success(
            request,
            (
                f'Admin account "{admin_user.username}" '
                f"was activated successfully."
            ),
        )

    else:

        messages.warning(
            request,
            (
                f'Admin account "{admin_user.username}" '
                f"was deactivated."
            ),
        )

    return redirect(
        "manage_admin_accounts"
    )


# ==========================================================
# ADMIN - MANAGE PUBLICATION STAFF
# ==========================================================


@role_required(User.Role.ADMIN)
def manage_staff_accounts(request):

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    selected_role = request.GET.get(
        "role",
        "ALL",
    )

    allowed_roles = [
        User.Role.ADVISER,
        User.Role.EIC,
        User.Role.EDITOR,
        User.Role.STAFF,
    ]

    staff_accounts = User.objects.filter(
        role__in=allowed_roles
    )

    if selected_role in allowed_roles:

        staff_accounts = (
            staff_accounts.filter(
                role=selected_role
            )
        )

    if search_query:

        staff_accounts = (
            staff_accounts.filter(
                Q(
                    username__icontains=search_query
                )
                | Q(
                    first_name__icontains=search_query
                )
                | Q(
                    last_name__icontains=search_query
                )
                | Q(
                    email__icontains=search_query
                )
            )
        )

    staff_accounts = (
        staff_accounts.order_by(
            "role",
            "username",
        )
    )

    return render(
        request,
        "accounts/manage_staff.html",
        {
            "staff_accounts": staff_accounts,
            "search_query": search_query,
            "selected_role": selected_role,
            "role_choices": [
                (
                    User.Role.ADVISER,
                    User.Role.ADVISER.label,
                ),
                (
                    User.Role.EIC,
                    User.Role.EIC.label,
                ),
                (
                    User.Role.EDITOR,
                    User.Role.EDITOR.label,
                ),
                (
                    User.Role.STAFF,
                    User.Role.STAFF.label,
                ),
            ],
        },
    )


@role_required(User.Role.ADMIN)
def create_staff_account(request):

    if request.method == "POST":

        form = StaffAccountCreationForm(
            request.POST
        )

        if form.is_valid():

            staff_user = form.save()

            messages.success(
                request,
                (
                    f'Account "{staff_user.username}" '
                    f"was created successfully as "
                    f"{staff_user.get_role_display()}."
                ),
            )

            return redirect(
                "manage_staff_accounts"
            )

        messages.error(
            request,
            "The account could not be created. Please check the form.",
        )

    else:

        form = StaffAccountCreationForm()

    return render(
        request,
        "accounts/create_staff_account.html",
        {
            "form": form,
        },
    )


@role_required(User.Role.ADMIN)
def edit_staff_account(
    request,
    user_id,
):

    allowed_roles = [
        User.Role.ADVISER,
        User.Role.EIC,
        User.Role.EDITOR,
        User.Role.STAFF,
    ]

    staff_user = get_object_or_404(
        User,
        id=user_id,
        role__in=allowed_roles,
    )

    if request.method == "POST":

        form = StaffAccountEditForm(
            request.POST,
            instance=staff_user,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                (
                    f'Account "{staff_user.username}" '
                    f"was updated successfully."
                ),
            )

            return redirect(
                "manage_staff_accounts"
            )

        messages.error(
            request,
            "The account could not be updated. Please check the form.",
        )

    else:

        form = StaffAccountEditForm(
            instance=staff_user
        )

    return render(
        request,
        "accounts/edit_staff_account.html",
        {
            "form": form,
            "managed_user": staff_user,
        },
    )


@role_required(User.Role.ADMIN)
def toggle_staff_account_status(
    request,
    user_id,
):

    if request.method != "POST":

        return redirect(
            "manage_staff_accounts"
        )

    allowed_roles = [
        User.Role.ADVISER,
        User.Role.EIC,
        User.Role.EDITOR,
        User.Role.STAFF,
    ]

    staff_user = get_object_or_404(
        User,
        id=user_id,
        role__in=allowed_roles,
    )

    staff_user.is_active = (
        not staff_user.is_active
    )

    staff_user.save(
        update_fields=[
            "is_active",
        ]
    )

    if staff_user.is_active:

        messages.success(
            request,
            (
                f'Account "{staff_user.username}" '
                f"was activated successfully."
            ),
        )

    else:

        messages.warning(
            request,
            (
                f'Account "{staff_user.username}" '
                f"was deactivated."
            ),
        )

    return redirect(
        "manage_staff_accounts"
    )
