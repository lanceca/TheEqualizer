from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import security_views, views
from .security_forms import (
    VerifiedPasswordResetForm,
)


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
    # EMAIL VERIFICATION
    # =========================

    path(
        "verify-email/pending/",
        security_views.verification_pending,
        name="verification_pending",
    ),

    path(
        "verify-email/resend/",
        security_views.resend_verification,
        name="resend_verification",
    ),

    path(
        "verify-email/<uidb64>/<token>/",
        security_views.verify_email,
        name="verify_email",
    ),

    # =========================
    # FORGOT PASSWORD
    # =========================

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name=(
                "accounts/"
                "password_reset_form.html"
            ),
            email_template_name=(
                "accounts/emails/"
                "password_reset_email.txt"
            ),
            subject_template_name=(
                "accounts/emails/"
                "password_reset_subject.txt"
            ),
            form_class=(
                VerifiedPasswordResetForm
            ),
            success_url=reverse_lazy(
                "password_reset_done"
            ),
        ),
        name="password_reset",
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name=(
                "accounts/"
                "password_reset_done.html"
            ),
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name=(
                "accounts/"
                "password_reset_confirm.html"
            ),
            success_url=reverse_lazy(
                "password_reset_complete"
            ),
        ),
        name="password_reset_confirm",
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name=(
                "accounts/"
                "password_reset_complete.html"
            ),
        ),
        name="password_reset_complete",
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
        "profile/change-email/",
        security_views.change_email,
        name="change_email",
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
