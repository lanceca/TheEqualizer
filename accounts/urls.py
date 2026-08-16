from django.urls import path

from . import views


urlpatterns = [
    path("dashboard/", views.dashboard_redirect, name="dashboard"),

    path(
        "dashboard/super-admin/",
        views.super_admin_dashboard,
        name="super_admin_dashboard",
    ),

    path(
        "dashboard/admin/",
        views.admin_dashboard,
        name="admin_dashboard",
    ),

    path(
        "dashboard/adviser/",
        views.adviser_dashboard,
        name="adviser_dashboard",
    ),

    path(
        "dashboard/eic/",
        views.eic_dashboard,
        name="eic_dashboard",
    ),

    path(
        "dashboard/editor/",
        views.editor_dashboard,
        name="editor_dashboard",
    ),

    path(
        "dashboard/staff/",
        views.staff_dashboard,
        name="staff_dashboard",
    ),

    path(
        "login/", views.login_view, name="login"
    ),

    path(
        "logout/", views.logout_view, name="logout"
    ),
]