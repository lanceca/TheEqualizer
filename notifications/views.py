from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .context_processors import get_workspace_activity
from .models import Notification




# ==========================================================
# LIVE WORKSPACE STATUS
# ==========================================================


@login_required
@never_cache
@require_GET
def notification_status(request):
    """
    Return the logged-in staff member's latest notification and the
    workflow counts used by the staff sidebar.

    The staff shell polls this endpoint while a tab is visible so the
    receiver sees new editorial activity without navigating or manually
    refreshing the page.
    """

    activity = get_workspace_activity(
        request.user
    )

    latest_notification = (
        Notification.objects
        .filter(
            recipient=request.user
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )

    latest_payload = None

    if latest_notification is not None:
        latest_payload = {
            "id": latest_notification.id,
            "notification_type": (
                latest_notification.notification_type
            ),
            "type_label": (
                latest_notification.get_notification_type_display()
            ),
            "message": latest_notification.message,
            "related_url": latest_notification.related_url,
            "is_read": latest_notification.is_read,
            "created_at": (
                latest_notification.created_at.isoformat()
            ),
        }

    response = JsonResponse(
        {
            "unread_notification_count": activity[
                "global_unread_notification_count"
            ],
            "latest_notification_id": activity[
                "global_latest_notification_id"
            ],
            "latest_notification": latest_payload,
            "workflow": {
                "pending_submissions": activity[
                    "sidebar_pending_submissions_count"
                ],
                "pending_edit_requests": activity[
                    "sidebar_pending_edit_requests_count"
                ],
                "pending_deletion_requests": activity[
                    "sidebar_pending_deletion_requests_count"
                ],
                "active_content_reports": activity[
                    "sidebar_active_content_reports_count"
                ],
                "editor_current_submissions": activity[
                    "sidebar_editor_current_submissions_count"
                ],
                "editor_resubmissions": activity[
                    "sidebar_editor_resubmissions_count"
                ],
                "editor_edit_requests": activity[
                    "sidebar_editor_edit_requests_count"
                ],
                "editor_deletion_requests": activity[
                    "sidebar_editor_deletion_requests_count"
                ],
                "staff_active_reports": activity[
                    "sidebar_staff_active_reports_count"
                ],
            },
        }
    )

    # Explicit no-store headers keep browser/proxy caches from serving stale
    # counts to an already-open staff page.
    response["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response["Pragma"] = "no-cache"

    return response


# ==========================================================
# NOTIFICATION LIST
# ==========================================================


@login_required
def notification_list(request):

    selected_filter = request.GET.get(
        "filter",
        "all",
    ).lower()

    if selected_filter not in {
        "all",
        "unread",
        "read",
    }:
        selected_filter = "all"

    base_notifications = (
        Notification.objects
        .filter(
            recipient=request.user
        )
    )

    total_count = base_notifications.count()

    unread_count = (
        base_notifications
        .filter(
            is_read=False
        )
        .count()
    )

    read_count = (
        total_count
        - unread_count
    )

    notifications = base_notifications

    if selected_filter == "unread":

        notifications = (
            notifications.filter(
                is_read=False
            )
        )

    elif selected_filter == "read":

        notifications = (
            notifications.filter(
                is_read=True
            )
        )

    notifications = (
        notifications.order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
            "read_count": read_count,
            "total_count": total_count,
            "selected_filter": (
                selected_filter
            ),
        },
    )


# ==========================================================
# MARK SINGLE NOTIFICATION AS READ
# ==========================================================


@login_required
@require_POST
def mark_notification_read(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )

    if not notification.is_read:

        notification.is_read = True

        notification.save(
            update_fields=[
                "is_read",
            ]
        )

    if notification.related_url:

        return redirect(
            notification.related_url
        )

    messages.success(
        request,
        "Notification marked as read.",
    )

    return redirect(
        "notification_list"
    )


# ==========================================================
# MARK ALL NOTIFICATIONS AS READ
# ==========================================================


@login_required
@require_POST
def mark_all_notifications_read(request):

    updated_count = (
        Notification.objects
        .filter(
            recipient=request.user,
            is_read=False,
        )
        .update(
            is_read=True
        )
    )

    if updated_count > 0:

        messages.success(
            request,
            (
                f"{updated_count} notification"
                f"{'s' if updated_count != 1 else ''} "
                f"marked as read."
            ),
        )

    else:

        messages.info(
            request,
            "You have no unread notifications.",
        )

    return redirect(
        "notification_list"
    )


# ==========================================================
# CLEAR READ NOTIFICATIONS
# ==========================================================


@login_required
@require_POST
def clear_read_notifications(request):

    deleted_count, _ = (
        Notification.objects
        .filter(
            recipient=request.user,
            is_read=True,
        )
        .delete()
    )

    if deleted_count > 0:

        messages.success(
            request,
            (
                f"{deleted_count} read notification"
                f"{'s' if deleted_count != 1 else ''} "
                f"cleared."
            ),
        )

    else:

        messages.info(
            request,
            "There are no read notifications to clear.",
        )

    return redirect(
        "notification_list"
    )


# ==========================================================
# CLEAR ALL NOTIFICATIONS
# ==========================================================


@login_required
@require_POST
def clear_all_notifications(request):

    deleted_count, _ = (
        Notification.objects
        .filter(
            recipient=request.user
        )
        .delete()
    )

    if deleted_count > 0:

        messages.success(
            request,
            (
                f"{deleted_count} notification"
                f"{'s' if deleted_count != 1 else ''} "
                f"cleared."
            ),
        )

    else:

        messages.info(
            request,
            "You have no notifications to clear.",
        )

    return redirect(
        "notification_list"
    )
