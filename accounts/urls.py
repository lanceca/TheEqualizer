from django.urls import path

from . import views


urlpatterns = [
    # =========================
    # DASHBOARDS
    # =========================

    path(
        "dashboard/",
        views.dashboard_redirect,
        name="dashboard",
    ),

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
        "dashboard/adviser/report.pdf",
        views.download_adviser_analytics_pdf,
        name="download_adviser_analytics_pdf",
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

    # =========================
    # AUTHENTICATION
    # =========================

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),

    # =========================
    # PROFILE
    # =========================

    path(
        "profile/",
        views.profile,
        name="profile",
    ),

    path(
        "profile/change-username/",
        views.change_username,
        name="change_username",
    ),

    path(
        "profile/change-password/",
        views.change_password,
        name="change_password",
    ),

    # =========================
    # ADVISER / EIC DIRECTORY
    # =========================

    path(
        "staff-directory/",
        views.staff_directory,
        name="staff_directory",
    ),

    # =========================
    # SUPER ADMIN - ADMINS
    # =========================

    path(
        "accounts/admins/",
        views.manage_admin_accounts,
        name="manage_admin_accounts",
    ),

    path(
        "accounts/admins/create/",
        views.create_admin_account,
        name="create_admin_account",
    ),

    path(
        "accounts/admins/<int:user_id>/edit/",
        views.edit_admin_account,
        name="edit_admin_account",
    ),

    path(
        "accounts/admins/<int:user_id>/toggle-status/",
        views.toggle_admin_account_status,
        name="toggle_admin_account_status",
    ),

    # =========================
    # ADMIN - PUBLICATION STAFF
    # =========================

    path(
        "accounts/staff/",
        views.manage_staff_accounts,
        name="manage_staff_accounts",
    ),

    path(
        "accounts/staff/create/",
        views.create_staff_account,
        name="create_staff_account",
    ),

    path(
        "accounts/staff/<int:user_id>/edit/",
        views.edit_staff_account,
        name="edit_staff_account",
    ),

    path(
        "accounts/staff/<int:user_id>/toggle-status/",
        views.toggle_staff_account_status,
        name="toggle_staff_account_status",
    ),
]
