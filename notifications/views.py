from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notification


# ==========================================================
# NOTIFICATION LIST
# ==========================================================


@login_required
def notification_list(request):

    notifications = (
        Notification.objects
        .filter(
            recipient=request.user
        )
        .order_by("-created_at")
    )

    unread_count = notifications.filter(
        is_read=False
    ).count()

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


# ==========================================================
# MARK SINGLE NOTIFICATION AS READ
# ==========================================================


@login_required
def mark_notification_read(
    request,
    notification_id,
):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )

    if request.method == "POST":

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
def mark_all_notifications_read(request):

    if request.method == "POST":

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
                "All notifications have been marked as read.",
            )

        else:

            messages.info(
                request,
                "You have no unread notifications.",
            )

    return redirect(
        "notification_list"
    )