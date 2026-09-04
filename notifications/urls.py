from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.notification_list,
        name="notification_list",
    ),

    path(
        "<int:notification_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),

    path(
        "mark-all-read/",
        views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),

    path(
        "clear-read/",
        views.clear_read_notifications,
        name="clear_read_notifications",
    ),

    path(
        "clear-all/",
        views.clear_all_notifications,
        name="clear_all_notifications",
    ),
]
