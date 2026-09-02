from datetime import timedelta
from functools import wraps

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
from django.db.models import Count, Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

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

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Your profile was updated successfully.",
            )

            return redirect(
                "profile"
            )

        messages.error(
            request,
            "Your profile could not be updated. Please check the form.",
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