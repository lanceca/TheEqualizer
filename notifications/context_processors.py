from publications.models import (
    ContentReport,
    DeletionRequest,
    EditRequest,
    Submission,
)

from .models import Notification
from .updates import pending_updates


WORKSPACE_ACTIVITY_DEFAULTS = {
    "global_unread_notification_count": 0,
    "global_latest_notification_id": 0,

    "sidebar_pending_submissions_count": 0,
    "sidebar_pending_edit_requests_count": 0,
    "sidebar_pending_deletion_requests_count": 0,
    "sidebar_active_content_reports_count": 0,

    "sidebar_editor_current_submissions_count": 0,
    "sidebar_editor_resubmissions_count": 0,
    "sidebar_editor_edit_requests_count": 0,
    "sidebar_editor_deletion_requests_count": 0,

    "sidebar_staff_active_reports_count": 0,
}


def get_workspace_activity(user):
    """
    Return the live notification/workflow counts used by the staff shell.

    This helper is shared by the normal Django context processor and the
    lightweight polling endpoint so the first page render and live updates
    always use the same queries and business rules.
    """

    activity = WORKSPACE_ACTIVITY_DEFAULTS.copy()

    if not getattr(user, "is_authenticated", False):
        return activity

    user_notifications = Notification.objects.filter(
        recipient=user,
    )

    activity[
        "global_unread_notification_count"
    ] = user_notifications.filter(
        is_read=False,
    ).count()

    activity[
        "global_latest_notification_id"
    ] = (
        user_notifications
        .order_by("-created_at", "-id")
        .values_list("id", flat=True)
        .first()
        or 0
    )

    role = getattr(
        user,
        "role",
        "",
    )

    if role == "EIC":

        activity[
            "sidebar_pending_submissions_count"
        ] = (
            Submission.objects
            .filter(
                status=Submission.Status.PENDING
            )
            .count()
        )

        activity[
            "sidebar_pending_edit_requests_count"
        ] = (
            EditRequest.objects
            .filter(
                status=EditRequest.Status.PENDING
            )
            .count()
        )

        activity[
            "sidebar_pending_deletion_requests_count"
        ] = (
            DeletionRequest.objects
            .filter(
                status=DeletionRequest.Status.PENDING
            )
            .count()
        )

        activity[
            "sidebar_active_content_reports_count"
        ] = (
            ContentReport.objects
            .filter(
                status__in=[
                    ContentReport.Status.OPEN,
                    ContentReport.Status.REVISION_REQUIRED,
                ]
            )
            .count()
        )

    elif role == "EDITOR":

        activity[
            "sidebar_editor_current_submissions_count"
        ] = (
            Submission.objects
            .filter(
                submitted_by=user,
                resubmission_of__isnull=True,
                resubmissions__isnull=True,
                status__in=[
                    Submission.Status.PENDING,
                    Submission.Status.REVISION,
                ],
            )
            .distinct()
            .count()
        )

        activity[
            "sidebar_editor_resubmissions_count"
        ] = (
            Submission.objects
            .filter(
                submitted_by=user,
                resubmission_of__isnull=False,
                resubmissions__isnull=True,
                status__in=[
                    Submission.Status.PENDING,
                    Submission.Status.REVISION,
                ],
            )
            .distinct()
            .count()
        )

        activity[
            "sidebar_editor_edit_requests_count"
        ] = (
            EditRequest.objects
            .filter(
                requested_by=user,
                status__in=[
                    EditRequest.Status.PENDING,
                    EditRequest.Status.APPROVED,
                ],
            )
            .count()
        )

        activity[
            "sidebar_editor_deletion_requests_count"
        ] = (
            DeletionRequest.objects
            .filter(
                requested_by=user,
                status=DeletionRequest.Status.PENDING,
            )
            .count()
        )

    elif role == "STAFF":

        activity[
            "sidebar_staff_active_reports_count"
        ] = (
            ContentReport.objects
            .filter(
                reported_by=user,
                status__in=[
                    ContentReport.Status.OPEN,
                    ContentReport.Status.REVISION_REQUIRED,
                ],
            )
            .count()
        )

    return activity


def notification_context(request):
    context = {
        "system_update_count": 0,
        **WORKSPACE_ACTIVITY_DEFAULTS,
    }

    if not request.user.is_authenticated:
        return context

    context.update(
        get_workspace_activity(
            request.user
        )
    )

    context[
        "system_update_count"
    ] = pending_updates(
        request.user
    ).count()

    return context
