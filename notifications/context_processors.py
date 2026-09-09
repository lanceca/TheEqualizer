from django.db.models import Q

from publications.models import (
    ContentReport,
    DeletionRequest,
    EditRequest,
    Submission,
)

from .models import Notification


def notification_context(request):

    defaults = {
        "global_unread_notification_count": 0,

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

    if not request.user.is_authenticated:
        return defaults

    defaults[
        "global_unread_notification_count"
    ] = (
        Notification.objects
        .filter(
            recipient=request.user,
            is_read=False,
        )
        .count()
    )

    role = getattr(
        request.user,
        "role",
        "",
    )

    if role == "EIC":

        defaults[
            "sidebar_pending_submissions_count"
        ] = (
            Submission.objects
            .filter(
                status=Submission.Status.PENDING
            )
            .count()
        )

        defaults[
            "sidebar_pending_edit_requests_count"
        ] = (
            EditRequest.objects
            .filter(
                status=EditRequest.Status.PENDING
            )
            .count()
        )

        defaults[
            "sidebar_pending_deletion_requests_count"
        ] = (
            DeletionRequest.objects
            .filter(
                status=DeletionRequest.Status.PENDING
            )
            .count()
        )

        defaults[
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

        defaults[
            "sidebar_editor_current_submissions_count"
        ] = (
            Submission.objects
            .filter(
                submitted_by=request.user,
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

        defaults[
            "sidebar_editor_resubmissions_count"
        ] = (
            Submission.objects
            .filter(
                submitted_by=request.user,
                resubmission_of__isnull=False,
                status__in=[
                    Submission.Status.PENDING,
                    Submission.Status.REVISION,
                ],
            )
            .count()
        )

        defaults[
            "sidebar_editor_edit_requests_count"
        ] = (
            EditRequest.objects
            .filter(
                requested_by=request.user,
                status__in=[
                    EditRequest.Status.PENDING,
                    EditRequest.Status.APPROVED,
                ],
            )
            .count()
        )

        defaults[
            "sidebar_editor_deletion_requests_count"
        ] = (
            DeletionRequest.objects
            .filter(
                requested_by=request.user,
                status=DeletionRequest.Status.PENDING,
            )
            .count()
        )

    elif role == "STAFF":

        defaults[
            "sidebar_staff_active_reports_count"
        ] = (
            ContentReport.objects
            .filter(
                reported_by=request.user,
                status__in=[
                    ContentReport.Status.OPEN,
                    ContentReport.Status.REVISION_REQUIRED,
                ],
            )
            .count()
        )

    return defaults
