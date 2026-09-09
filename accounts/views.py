import io
import logging
from datetime import date, timedelta
from functools import wraps
from html import escape

from django.contrib import messages
from django.contrib.staticfiles import finders
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
from django.db.models import BigIntegerField, Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as PDFImage,
    KeepTogether,
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

logger = logging.getLogger(__name__)


# ==========================================================
# STORAGE CLEANUP HELPER
# ==========================================================


def delete_storage_file_safely(file_name):
    """
    Remove an obsolete profile image without allowing a temporary
    Supabase/S3 cleanup failure to turn a successful profile update
    into a server error.
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
                "Non-fatal profile media cleanup failed "
                "for storage object %s."
            ),
            file_name,
        )
        return False

    return True


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
            "adviser_overview"
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


ADVISER_ANALYTICS_DEFAULT_RANGE = "30"
ADVISER_ANALYTICS_SCHOOL_YEAR_START_MONTH = 6


def get_adviser_analytics_period(request):
    """
    Resolve the Adviser reporting period from GET parameters.

    Supported range values:
    all, 7, 30, month, school_year, custom.
    """

    today = timezone.localdate()

    selected_range = (
        request.GET.get(
            "range",
            ADVISER_ANALYTICS_DEFAULT_RANGE,
        )
        .strip()
        .lower()
    )

    valid_ranges = {
        "all",
        "7",
        "30",
        "month",
        "school_year",
        "custom",
    }

    filter_error = ""

    if selected_range not in valid_ranges:
        selected_range = (
            ADVISER_ANALYTICS_DEFAULT_RANGE
        )

    start_date = None
    end_date = today

    if selected_range == "7":
        start_date = today - timedelta(days=6)
        period_label = "Last 7 Days"

    elif selected_range == "30":
        start_date = today - timedelta(days=29)
        period_label = "Last 30 Days"

    elif selected_range == "month":
        start_date = today.replace(day=1)
        period_label = "This Month"

    elif selected_range == "school_year":

        school_year_start_year = (
            today.year
            if today.month
            >= ADVISER_ANALYTICS_SCHOOL_YEAR_START_MONTH
            else today.year - 1
        )

        start_date = date(
            school_year_start_year,
            ADVISER_ANALYTICS_SCHOOL_YEAR_START_MONTH,
            1,
        )

        period_label = (
            f"School Year "
            f"{school_year_start_year}–"
            f"{school_year_start_year + 1}"
        )

    elif selected_range == "custom":

        custom_start = (
            request.GET.get(
                "start",
                "",
            )
            .strip()
        )

        custom_end = (
            request.GET.get(
                "end",
                "",
            )
            .strip()
        )

        try:
            start_date = date.fromisoformat(
                custom_start
            )
            end_date = date.fromisoformat(
                custom_end
            )
        except ValueError:
            filter_error = (
                "Choose valid start and end dates. "
                "The Last 30 Days range is being shown instead."
            )
            selected_range = (
                ADVISER_ANALYTICS_DEFAULT_RANGE
            )
            start_date = (
                today - timedelta(days=29)
            )
            end_date = today
            period_label = "Last 30 Days"
        else:

            if end_date > today:
                end_date = today

            if start_date > end_date:
                filter_error = (
                    "The start date cannot be later than the end date. "
                    "The Last 30 Days range is being shown instead."
                )
                selected_range = (
                    ADVISER_ANALYTICS_DEFAULT_RANGE
                )
                start_date = (
                    today - timedelta(days=29)
                )
                end_date = today
                period_label = "Last 30 Days"
            else:
                period_label = (
                    f"{start_date.strftime('%b %d, %Y')} "
                    f"to {end_date.strftime('%b %d, %Y')}"
                )

    else:
        period_label = "All Tracked History"

    return {
        "selected_range": selected_range,
        "start_date": start_date,
        "end_date": end_date,
        "period_label": period_label,
        "filter_error": filter_error,
    }


def filter_datetime_queryset_by_period(
    queryset,
    field_name,
    start_date,
    end_date,
):
    """
    Filter a queryset by the calendar date portion of a DateTimeField.
    """

    filters = {
        f"{field_name}__date__lte": end_date,
    }

    if start_date is not None:
        filters[
            f"{field_name}__date__gte"
        ] = start_date

    return queryset.filter(
        **filters
    )


def build_datetime_period_q(
    field_name,
    start_date,
    end_date,
):
    """
    Build a Q object for a DateTimeField restricted to the selected period.
    """

    period_q = Q(
        **{
            f"{field_name}__date__lte": (
                end_date
            )
        }
    )

    if start_date is not None:
        period_q &= Q(
            **{
                f"{field_name}__date__gte": (
                    start_date
                )
            }
        )

    return period_q


def build_daily_analytics_period_q(
    relation_prefix,
    start_date,
    end_date,
):
    """
    Build a Q object for the DateField used by ArticleDailyAnalytics.
    """

    period_q = Q(
        **{
            f"{relation_prefix}__date__lte": (
                end_date
            )
        }
    )

    if start_date is not None:
        period_q &= Q(
            **{
                f"{relation_prefix}__date__gte": (
                    start_date
                )
            }
        )

    return period_q


def get_adviser_analytics_data(request):
    """
    Build the Adviser analytics data shared by the dashboard and PDF export.

    Publication status and workflow-health cards remain current snapshots.
    Historical engagement, submission analytics, content performance, and
    editor performance follow the selected reporting period.
    """

    period = get_adviser_analytics_period(
        request
    )

    analytics_range = period[
        "selected_range"
    ]
    analytics_start_date = period[
        "start_date"
    ]
    analytics_end_date = period[
        "end_date"
    ]

    # ======================================================
    # BASE QUERYSETS
    # ======================================================

    normal_articles = Article.objects.filter(
        draft_type=Article.DraftType.NORMAL
    )

    published_queryset = (
        normal_articles
        .filter(
            is_published=True,
            is_archived=False,
        )
    )

    # ======================================================
    # CURRENT PUBLICATION SNAPSHOT
    # ======================================================

    total_articles = (
        normal_articles.count()
    )

    published_articles = (
        published_queryset.count()
    )

    archived_articles = (
        normal_articles
        .filter(
            is_archived=True,
        )
        .count()
    )

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

    # ======================================================
    # SUBMISSION ANALYTICS - SELECTED PERIOD
    # ======================================================

    period_submissions = (
        filter_datetime_queryset_by_period(
            Submission.objects.all(),
            "submitted_at",
            analytics_start_date,
            analytics_end_date,
        )
    )

    total_submissions = (
        period_submissions.count()
    )

    pending_submissions = (
        period_submissions
        .filter(
            status=Submission.Status.PENDING
        )
        .count()
    )

    approved_submissions = (
        period_submissions
        .filter(
            status=Submission.Status.APPROVED
        )
        .count()
    )

    rejected_submissions = (
        period_submissions
        .filter(
            status=Submission.Status.REJECTED
        )
        .count()
    )

    revision_submissions = (
        period_submissions
        .filter(
            status=Submission.Status.REVISION
        )
        .count()
    )

    # ======================================================
    # CURRENT WORKFLOW HEALTH
    # ======================================================

    pending_edit_requests = (
        EditRequest.objects
        .filter(
            status=EditRequest.Status.PENDING
        )
        .count()
    )

    approved_edit_requests = (
        EditRequest.objects
        .filter(
            status=EditRequest.Status.APPROVED
        )
        .count()
    )

    rejected_edit_requests = (
        EditRequest.objects
        .filter(
            status=EditRequest.Status.REJECTED
        )
        .count()
    )

    completed_edit_requests = (
        EditRequest.objects
        .filter(
            status=EditRequest.Status.COMPLETED
        )
        .count()
    )

    pending_deletion_requests = (
        DeletionRequest.objects
        .filter(
            status=DeletionRequest.Status.PENDING
        )
        .count()
    )

    approved_deletion_requests = (
        DeletionRequest.objects
        .filter(
            status=DeletionRequest.Status.APPROVED
        )
        .count()
    )

    rejected_deletion_requests = (
        DeletionRequest.objects
        .filter(
            status=DeletionRequest.Status.REJECTED
        )
        .count()
    )

    open_content_reports = (
        ContentReport.objects
        .filter(
            status=ContentReport.Status.OPEN
        )
        .count()
    )

    revision_required_reports = (
        ContentReport.objects
        .filter(
            status=(
                ContentReport.Status.REVISION_REQUIRED
            )
        )
        .count()
    )

    cancelled_content_reports = (
        ContentReport.objects
        .filter(
            status=ContentReport.Status.CANCELLED
        )
        .count()
    )

    resolved_content_reports = (
        ContentReport.objects
        .filter(
            status=ContentReport.Status.RESOLVED
        )
        .count()
    )

    active_content_reports = (
        open_content_reports
        + revision_required_reports
    )

    total_content_reports = (
        ContentReport.objects.count()
    )

    # ======================================================
    # READER ENGAGEMENT - SELECTED PERIOD
    # ======================================================

    daily_analytics = (
        ArticleDailyAnalytics.objects
        .filter(
            article__draft_type=(
                Article.DraftType.NORMAL
            ),
            date__lte=analytics_end_date,
        )
    )

    if analytics_start_date is not None:
        daily_analytics = (
            daily_analytics.filter(
                date__gte=analytics_start_date
            )
        )

    reader_totals = (
        daily_analytics.aggregate(
            total_views=Sum("views"),
            total_reactions=Sum(
                "reactions"
            ),
            total_shares=Sum("shares"),
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

    daily_engagement_rows = (
        daily_analytics
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
            "reactions": (
                row["reactions"]
                or 0
            ),
            "shares": row["shares"] or 0,
        }
        for row in daily_engagement_rows
    }

    chart_start_date = (
        analytics_start_date
    )

    if chart_start_date is None:
        chart_start_date = (
            daily_analytics
            .order_by("date")
            .values_list(
                "date",
                flat=True,
            )
            .first()
            or analytics_end_date
        )

    historical_engagement_labels = []
    historical_engagement_full_dates = []
    historical_views = []
    historical_reactions = []
    historical_shares = []

    chart_day_count = (
        analytics_end_date
        - chart_start_date
    ).days + 1

    for day_offset in range(
        max(chart_day_count, 1)
    ):

        current_date = (
            chart_start_date
            + timedelta(
                days=day_offset
            )
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
            current_date.strftime(
                "%b %d"
            )
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

    # ======================================================
    # EDITOR PERFORMANCE - SELECTED PERIOD
    # ======================================================

    editor_article_filter = Q(
        articles__draft_type=(
            Article.DraftType.NORMAL
        )
    ) & build_datetime_period_q(
        "articles__created_at",
        analytics_start_date,
        analytics_end_date,
    )

    editor_published_filter = Q(
        articles__draft_type=(
            Article.DraftType.NORMAL
        ),
        articles__published_at__isnull=False,
    ) & build_datetime_period_q(
        "articles__published_at",
        analytics_start_date,
        analytics_end_date,
    )

    editor_submission_filter = (
        build_datetime_period_q(
            "submissions__submitted_at",
            analytics_start_date,
            analytics_end_date,
        )
    )

    editors = (
        User.objects
        .filter(
            role=User.Role.EDITOR
        )
        .annotate(
            article_count=Count(
                "articles",
                filter=editor_article_filter,
                distinct=True,
            ),
            published_count=Count(
                "articles",
                filter=editor_published_filter,
                distinct=True,
            ),
            submission_count=Count(
                "submissions",
                filter=editor_submission_filter,
                distinct=True,
            ),
            pending_count=Count(
                "submissions",
                filter=(
                    editor_submission_filter
                    & Q(
                        submissions__status=(
                            Submission.Status.PENDING
                        )
                    )
                ),
                distinct=True,
            ),
            approved_count=Count(
                "submissions",
                filter=(
                    editor_submission_filter
                    & Q(
                        submissions__status=(
                            Submission.Status.APPROVED
                        )
                    )
                ),
                distinct=True,
            ),
            rejected_count=Count(
                "submissions",
                filter=(
                    editor_submission_filter
                    & Q(
                        submissions__status=(
                            Submission.Status.REJECTED
                        )
                    )
                ),
                distinct=True,
            ),
            revision_count=Count(
                "submissions",
                filter=(
                    editor_submission_filter
                    & Q(
                        submissions__status=(
                            Submission.Status.REVISION
                        )
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
    # CONTENT PERFORMANCE - SELECTED PERIOD
    # ======================================================

    daily_relation_filter = (
        build_daily_analytics_period_q(
            "daily_analytics",
            analytics_start_date,
            analytics_end_date,
        )
    )

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
            total_views=Coalesce(
                Sum(
                    "daily_analytics__views",
                    filter=(
                        daily_relation_filter
                    ),
                ),
                Value(0),
                output_field=BigIntegerField(),
            ),
            total_reactions=Coalesce(
                Sum(
                    "daily_analytics__reactions",
                    filter=(
                        daily_relation_filter
                    ),
                ),
                Value(0),
                output_field=BigIntegerField(),
            ),
            total_shares=Coalesce(
                Sum(
                    "daily_analytics__shares",
                    filter=(
                        daily_relation_filter
                    ),
                ),
                Value(0),
                output_field=BigIntegerField(),
            ),
        )
        .order_by(
            "-total_views",
            "-article_count",
            "category__name",
        )
    )

    period_article_queryset = (
        published_queryset
        .select_related(
            "category",
            "author",
        )
        .annotate(
            period_views=Coalesce(
                Sum(
                    "daily_analytics__views",
                    filter=(
                        daily_relation_filter
                    ),
                ),
                Value(0),
                output_field=BigIntegerField(),
            ),
            period_reactions=Coalesce(
                Sum(
                    "daily_analytics__reactions",
                    filter=(
                        daily_relation_filter
                    ),
                ),
                Value(0),
                output_field=BigIntegerField(),
            ),
            period_shares=Coalesce(
                Sum(
                    "daily_analytics__shares",
                    filter=(
                        daily_relation_filter
                    ),
                ),
                Value(0),
                output_field=BigIntegerField(),
            ),
        )
    )

    # Top Performing Articles is intentionally ranked by the
    # authoritative lifetime counters stored on Article. This prevents
    # older or partially backfilled daily-analytics rows from placing a
    # lower-viewed article above a genuinely higher-viewed article.
    top_viewed_articles = (
        published_queryset
        .select_related(
            "category",
            "author",
        )
        .order_by(
            "-view_count",
            "-reaction_count",
            "-share_count",
            "-published_at",
        )[:5]
    )

    top_reacted_articles = (
        period_article_queryset
        .order_by(
            "-period_reactions",
            "-published_at",
        )[:5]
    )

    top_shared_articles = (
        period_article_queryset
        .order_by(
            "-period_shares",
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
                category[
                    "category__name"
                ]
            ),
            "articles": (
                category["article_count"]
            ),
            "views": (
                category["total_views"]
                or 0
            ),
            "reactions": (
                category[
                    "total_reactions"
                ]
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
            "submissions": editor.submission_count,
            "pending": editor.pending_count,
            "approved": editor.approved_count,
            "rejected": editor.rejected_count,
            "revision": editor.revision_count,
        }
        for editor in editors
    ]

    return {
        "analytics_range": analytics_range,
        "analytics_period_label": (
            period["period_label"]
        ),
        "analytics_filter_error": (
            period["filter_error"]
        ),
        "analytics_start_date": (
            analytics_start_date
            or chart_start_date
        ),
        "analytics_end_date": (
            analytics_end_date
        ),
        "analytics_custom_start_value": (
            (
                analytics_start_date
                or chart_start_date
            ).isoformat()
        ),
        "analytics_custom_end_value": (
            analytics_end_date.isoformat()
        ),
        "analytics_is_all_time": (
            analytics_range == "all"
        ),
        "school_year_start_month": (
            ADVISER_ANALYTICS_SCHOOL_YEAR_START_MONTH
        ),

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

        "historical_engagement_labels": (
            historical_engagement_labels
        ),
        "historical_engagement_full_dates": (
            historical_engagement_full_dates
        ),
        "historical_views": historical_views,
        "historical_reactions": (
            historical_reactions
        ),
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


@role_required(User.Role.ADVISER)
def adviser_overview(request):

    context = {
        "overview_published_articles": (
            Article.objects
            .filter(
                draft_type=Article.DraftType.NORMAL,
                is_published=True,
                is_archived=False,
            )
            .count()
        ),
        "overview_pending_submissions": (
            Submission.objects
            .filter(
                status=Submission.Status.PENDING
            )
            .count()
        ),
        "overview_pending_edit_requests": (
            EditRequest.objects
            .filter(
                status=EditRequest.Status.PENDING
            )
            .count()
        ),
        "overview_active_content_reports": (
            ContentReport.objects
            .filter(
                status__in=[
                    ContentReport.Status.OPEN,
                    ContentReport.Status.REVISION_REQUIRED,
                ]
            )
            .count()
        ),
        "overview_active_staff": (
            User.objects
            .filter(
                is_active=True,
                role__in=[
                    User.Role.EIC,
                    User.Role.EDITOR,
                    User.Role.STAFF,
                ],
            )
            .count()
        ),
    }

    return render(
        request,
        "accounts/dashboards/adviser_overview.html",
        context,
    )


@role_required(User.Role.ADVISER)
def adviser_dashboard(request):

    context = get_adviser_analytics_data(
        request
    )

    return render(
        request,
        "accounts/dashboards/adviser.html",
        context,
    )


def equalizer_report_logo(width=0.56 * inch):
    """Return the bundled Equalizer logo for analytics PDF branding."""

    logo_path = finders.find("images/equalizer-logo.jpg")

    if not logo_path:
        return None

    try:
        logo = PDFImage(logo_path)
        ratio = logo.imageHeight / max(
            logo.imageWidth,
            1,
        )
        logo.drawWidth = width
        logo.drawHeight = width * ratio
        return logo
    except Exception:
        return None


def draw_adviser_report_page(canvas, document):
    """Draw the branded footer on every Adviser analytics report page."""

    page_width, _ = landscape(letter)

    canvas.saveState()
    canvas.setStrokeColor(
        colors.HexColor("#d7dfdb")
    )
    canvas.setLineWidth(0.6)
    canvas.line(
        document.leftMargin,
        0.48 * inch,
        page_width - document.rightMargin,
        0.48 * inch,
    )
    canvas.setFillColor(
        colors.HexColor("#65736d")
    )
    canvas.setFont("Helvetica", 7.6)
    canvas.drawString(
        document.leftMargin,
        0.27 * inch,
        "The Equalizer · Adviser Analytics",
    )
    canvas.drawCentredString(
        page_width / 2,
        0.27 * inch,
        timezone.localtime().strftime(
            "Generated %b %d, %Y · %I:%M %p"
        ),
    )
    canvas.drawRightString(
        page_width - document.rightMargin,
        0.27 * inch,
        f"Page {document.page}",
    )
    canvas.restoreState()


@role_required(User.Role.ADVISER)
def download_adviser_analytics_pdf(request):
    """Download a branded Adviser analytics report for the selected period."""

    analytics = get_adviser_analytics_data(
        request
    )

    analytics_start_date = analytics[
        "analytics_start_date"
    ]
    analytics_end_date = analytics[
        "analytics_end_date"
    ]
    analytics_period_label = analytics[
        "analytics_period_label"
    ]

    period_start_filter = (
        None
        if analytics["analytics_is_all_time"]
        else analytics_start_date
    )

    period_edit_requests = (
        filter_datetime_queryset_by_period(
            EditRequest.objects.all(),
            "created_at",
            period_start_filter,
            analytics_end_date,
        )
    )

    period_deletion_requests = (
        filter_datetime_queryset_by_period(
            DeletionRequest.objects.all(),
            "created_at",
            period_start_filter,
            analytics_end_date,
        )
    )

    period_content_reports = (
        filter_datetime_queryset_by_period(
            ContentReport.objects.all(),
            "created_at",
            period_start_filter,
            analytics_end_date,
        )
    )

    submission_counts = {
        status: (
            filter_datetime_queryset_by_period(
                Submission.objects.filter(
                    status=status
                ),
                "submitted_at",
                period_start_filter,
                analytics_end_date,
            ).count()
        )
        for status in [
            Submission.Status.PENDING,
            Submission.Status.APPROVED,
            Submission.Status.REJECTED,
            Submission.Status.REVISION,
        ]
    }

    edit_request_counts = {
        status: (
            period_edit_requests
            .filter(status=status)
            .count()
        )
        for status in [
            EditRequest.Status.PENDING,
            EditRequest.Status.APPROVED,
            EditRequest.Status.REJECTED,
            EditRequest.Status.COMPLETED,
        ]
    }

    deletion_request_counts = {
        status: (
            period_deletion_requests
            .filter(status=status)
            .count()
        )
        for status in [
            DeletionRequest.Status.PENDING,
            DeletionRequest.Status.APPROVED,
            DeletionRequest.Status.REJECTED,
        ]
    }

    content_report_counts = {
        status: (
            period_content_reports
            .filter(status=status)
            .count()
        )
        for status in [
            ContentReport.Status.OPEN,
            ContentReport.Status.REVISION_REQUIRED,
            ContentReport.Status.RESOLVED,
            ContentReport.Status.CANCELLED,
        ]
    }

    category_performance = list(
        analytics["category_performance"]
    )

    editors = list(
        analytics["editors"]
    )

    top_articles = list(
        analytics["top_viewed_articles"]
    )

    pdf_buffer = io.BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.52 * inch,
        bottomMargin=0.62 * inch,
        title="The Equalizer Adviser Analytics",
        author=request.user.username,
        subject="Publication analytics report",
    )

    sample_styles = getSampleStyleSheet()

    styles = {
        "brand": ParagraphStyle(
            "AnalyticsBrand",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=11,
            textColor=colors.HexColor(
                "#173f32"
            ),
            spaceAfter=1,
        ),
        "brand_sub": ParagraphStyle(
            "AnalyticsBrandSub",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor(
                "#65736d"
            ),
        ),
        "title": ParagraphStyle(
            "AnalyticsTitle",
            parent=sample_styles["Title"],
            fontName="Times-Bold",
            fontSize=24,
            leading=27,
            textColor=colors.HexColor(
                "#0e2a22"
            ),
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "AnalyticsSubtitle",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.4,
            leading=11,
            textColor=colors.HexColor(
                "#65736d"
            ),
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "AnalyticsHeading",
            parent=sample_styles["Heading2"],
            fontName="Times-Bold",
            fontSize=14.5,
            leading=18,
            textColor=colors.HexColor(
                "#173f32"
            ),
            spaceBefore=7,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "AnalyticsCell",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=9.5,
            textColor=colors.HexColor(
                "#24332d"
            ),
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor(
                "#65736d"
            ),
            alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue",
            parent=sample_styles["Normal"],
            fontName="Times-Bold",
            fontSize=18,
            leading=20,
            textColor=colors.HexColor(
                "#173f32"
            ),
            alignment=TA_CENTER,
        ),
    }

    table_style = TableStyle(
        [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#173f32"),
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold",
            ),
            (
                "FONTNAME",
                (0, 1),
                (-1, -1),
                "Helvetica",
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7.6,
            ),
            (
                "LEADING",
                (0, 0),
                (-1, -1),
                9.5,
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.HexColor("#cad5cf"),
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f3f7f5"),
                ],
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
        ]
    )

    def report_table(
        rows,
        widths=None,
        repeat_rows=1,
    ):
        table_class = (
            LongTable
            if len(rows) > 12
            else Table
        )

        table = table_class(
            rows,
            colWidths=widths,
            repeatRows=repeat_rows,
            hAlign="LEFT",
        )

        table.setStyle(
            table_style
        )

        return table

    def section_heading(text):
        return KeepTogether(
            [
                Paragraph(
                    text,
                    styles["heading"],
                ),
                HRFlowable(
                    width="100%",
                    thickness=0.7,
                    color=colors.HexColor(
                        "#d7dfdb"
                    ),
                    spaceAfter=7,
                ),
            ]
        )

    def kpi_card(label, value):
        return [
            Paragraph(
                str(value),
                styles["kpi_value"],
            ),
            Spacer(1, 2),
            Paragraph(
                label,
                styles["kpi_label"],
            ),
        ]

    logo = equalizer_report_logo()

    brand_text = [
        Paragraph(
            "THE EQUALIZER",
            styles["brand"],
        ),
        Paragraph(
            (
                "The Official Student Publication "
                "of Mabalacat City College"
            ),
            styles["brand_sub"],
        ),
    ]

    brand_table = Table(
        [[logo or "", brand_text]],
        colWidths=[
            0.7 * inch,
            8.95 * inch,
        ],
    )

    brand_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    period_start_text = (
        "Tracking start"
        if analytics["analytics_is_all_time"]
        else analytics_start_date.strftime(
            "%b %d, %Y"
        )
    )

    kpi_table = Table(
        [
            [
                kpi_card(
                    "Published articles",
                    analytics[
                        "published_articles"
                    ],
                ),
                kpi_card(
                    "Views",
                    analytics["total_views"],
                ),
                kpi_card(
                    "Reactions",
                    analytics[
                        "total_reactions"
                    ],
                ),
                kpi_card(
                    "Shares",
                    analytics["total_shares"],
                ),
                kpi_card(
                    "Total engagement",
                    analytics[
                        "total_engagement"
                    ],
                ),
            ]
        ],
        colWidths=[1.92 * inch] * 5,
        hAlign="LEFT",
    )

    kpi_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f4f7f5"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#d7dfdb"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    colors.HexColor("#d7dfdb"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story = [
        brand_table,
        Spacer(1, 7),
        HRFlowable(
            width="100%",
            thickness=1.1,
            color=colors.HexColor("#c9a227"),
            spaceAfter=10,
        ),
        Paragraph(
            "Adviser Analytics Report",
            styles["title"],
        ),
        Paragraph(
            (
                f"{escape(analytics_period_label)} · "
                f"Through "
                f"{analytics_end_date.strftime('%B %d, %Y')} "
                f"(Asia/Manila) · Prepared for "
                f"{escape(request.user.username)}"
            ),
            styles["subtitle"],
        ),
        kpi_table,
        Spacer(1, 11),
        section_heading(
            "Publication snapshot"
        ),
        report_table(
            [
                [
                    "Articles",
                    "Published",
                    "Draft",
                    "Archived",
                ],
                [
                    analytics["total_articles"],
                    analytics[
                        "published_articles"
                    ],
                    analytics["draft_articles"],
                    analytics[
                        "archived_articles"
                    ],
                ],
            ],
            [2.4 * inch] * 4,
        ),
        Spacer(1, 10),
        section_heading(
            "Reader engagement for selected period"
        ),
        report_table(
            [
                [
                    "Date range",
                    "Views",
                    "Reactions",
                    "Shares",
                    "Total engagement",
                ],
                [
                    (
                        f"{period_start_text} – "
                        f"{analytics_end_date:%b %d, %Y}"
                    ),
                    analytics["total_views"],
                    analytics[
                        "total_reactions"
                    ],
                    analytics["total_shares"],
                    analytics[
                        "total_engagement"
                    ],
                ],
            ],
            [
                2.8 * inch,
                1.65 * inch,
                1.65 * inch,
                1.65 * inch,
                1.85 * inch,
            ],
        ),
        Spacer(1, 10),
        section_heading(
            "Editorial workflow created in selected period"
        ),
        report_table(
            [
                [
                    "Workflow",
                    "Pending/Open",
                    "Approved/Resolved",
                    "Rejected/Cancelled",
                    "Revision/Completed",
                ],
                [
                    "Submissions",
                    submission_counts[
                        Submission.Status.PENDING
                    ],
                    submission_counts[
                        Submission.Status.APPROVED
                    ],
                    submission_counts[
                        Submission.Status.REJECTED
                    ],
                    submission_counts[
                        Submission.Status.REVISION
                    ],
                ],
                [
                    "Edit requests",
                    edit_request_counts[
                        EditRequest.Status.PENDING
                    ],
                    edit_request_counts[
                        EditRequest.Status.APPROVED
                    ],
                    edit_request_counts[
                        EditRequest.Status.REJECTED
                    ],
                    edit_request_counts[
                        EditRequest.Status.COMPLETED
                    ],
                ],
                [
                    "Deletion requests",
                    deletion_request_counts[
                        DeletionRequest.Status.PENDING
                    ],
                    deletion_request_counts[
                        DeletionRequest.Status.APPROVED
                    ],
                    deletion_request_counts[
                        DeletionRequest.Status.REJECTED
                    ],
                    "—",
                ],
                [
                    "Content reports",
                    content_report_counts[
                        ContentReport.Status.OPEN
                    ],
                    content_report_counts[
                        ContentReport.Status.RESOLVED
                    ],
                    content_report_counts[
                        ContentReport.Status.CANCELLED
                    ],
                    content_report_counts[
                        ContentReport.Status.REVISION_REQUIRED
                    ],
                ],
            ],
            [
                1.7 * inch,
                1.9 * inch,
                2.0 * inch,
                2.0 * inch,
                2.0 * inch,
            ],
        ),
        PageBreak(),
        section_heading(
            "Category performance"
        ),
        report_table(
            [
                [
                    "Category",
                    "Current published articles",
                    "Views",
                    "Reactions",
                    "Shares",
                ]
            ]
            + [
                [
                    Paragraph(
                        escape(
                            row[
                                "category__name"
                            ]
                            or "Uncategorized"
                        ),
                        styles["cell"],
                    ),
                    row["article_count"],
                    row["total_views"] or 0,
                    row[
                        "total_reactions"
                    ]
                    or 0,
                    row["total_shares"] or 0,
                ]
                for row in category_performance
            ],
            [
                2.9 * inch,
                2.05 * inch,
                1.35 * inch,
                1.35 * inch,
                1.35 * inch,
            ],
        ),
        Spacer(1, 13),
        section_heading(
            "Editor performance"
        ),
        report_table(
            [
                [
                    "Editor",
                    "Articles created",
                    "Published",
                    "Submissions",
                    "Approved",
                    "Revision",
                ]
            ]
            + [
                [
                    Paragraph(
                        escape(
                            editor.username
                        ),
                        styles["cell"],
                    ),
                    editor.article_count,
                    editor.published_count,
                    editor.submission_count,
                    editor.approved_count,
                    editor.revision_count,
                ]
                for editor in editors
            ],
            [
                2.35 * inch,
                1.45 * inch,
                1.35 * inch,
                1.45 * inch,
                1.35 * inch,
                1.35 * inch,
            ],
        ),
        PageBreak(),
        section_heading(
            "Top published articles"
        ),
        report_table(
            [
                [
                    "Article",
                    "Category",
                    "Author",
                    "Views",
                    "Reactions",
                    "Shares",
                ]
            ]
            + [
                [
                    Paragraph(
                        escape(article.title),
                        styles["cell"],
                    ),
                    Paragraph(
                        escape(
                            article.category.name
                        ),
                        styles["cell"],
                    ),
                    Paragraph(
                        escape(
                            article.author.username
                        ),
                        styles["cell"],
                    ),
                    article.period_views or 0,
                    article.period_reactions or 0,
                    article.period_shares or 0,
                ]
                for article in top_articles
            ],
            [
                3.35 * inch,
                1.55 * inch,
                1.45 * inch,
                0.9 * inch,
                1.0 * inch,
                0.9 * inch,
            ],
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

    if analytics[
        "analytics_is_all_time"
    ]:
        period_filename = "all-time"
    else:
        period_filename = (
            f"{analytics_start_date.isoformat()}"
            f"-to-"
            f"{analytics_end_date.isoformat()}"
        )

    response["Content-Disposition"] = (
        "attachment; filename="
        "the-equalizer-adviser-analytics-"
        f"{period_filename}.pdf"
    )

    response[
        "X-Content-Type-Options"
    ] = "nosniff"

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

        candidate_user = (
            User.objects
            .filter(
                username=(username or "").strip()
            )
            .first()
        )

        if (
            candidate_user is not None
            and candidate_user.is_active
            and candidate_user.email
            and not candidate_user.email_verified
            and candidate_user.check_password(password or "")
        ):
            messages.error(
                request,
                (
                    "Your account exists, but your email "
                    "address has not been verified yet. "
                    "Verify your email or use Resend "
                    "verification email below."
                ),
            )

            return render(
                request,
                "accounts/login.html",
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
                    delete_storage_file_safely(
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
        User.Role.ADVISER,
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
        User.Role.ADVISER: 0,
        User.Role.EIC: 1,
        User.Role.EDITOR: 2,
        User.Role.STAFF: 3,
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
