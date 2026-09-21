from django.urls import path

from . import views, update_views


urlpatterns = [
    path("updates/", update_views.update_history, name="system_update_history"),
    path("updates/popup/", update_views.update_popup, name="system_update_popup"),
    path("updates/manage/", update_views.manage_updates, name="manage_system_updates"),
    path("updates/new/", update_views.update_form, name="create_system_update"),
    path("updates/<int:update_id>/", update_views.update_detail, name="system_update_detail"),
    path("updates/<int:update_id>/edit/", update_views.update_form, name="edit_system_update"),
    path("updates/<int:update_id>/action/", update_views.update_action, name="system_update_action"),
    path("updates/<int:update_id>/acknowledge/", update_views.acknowledge_update, name="acknowledge_system_update"),
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
