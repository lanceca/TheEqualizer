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
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

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
    Restrict a view to users with one of the specified roles.
    """

    def decorator(view_func):

        @wraps(view_func)
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


@login_required
def dashboard_redirect(request):
    """
    Send the authenticated user to the dashboard
    corresponding to their role.
    """

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


@role_required(User.Role.ADVISER)
def adviser_dashboard(request):

    return render(
        request,
        "accounts/dashboards/adviser.html",
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
            {
                "error": (
                    "Invalid username or password."
                ),
            },
        )

    return render(
        request,
        "accounts/login.html",
    )


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
        "home"
    )


# ==========================================================
# PROFILE MANAGEMENT
# ==========================================================


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
                    f'was created successfully.'
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
                    f'was updated successfully.'
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
                f'was activated successfully.'
            ),
        )

    else:

        messages.warning(
            request,
            (
                f'Admin account "{admin_user.username}" '
                f'was deactivated.'
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
                    f'was created successfully as '
                    f'{staff_user.get_role_display()}.'
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
                    f'was updated successfully.'
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
                f'was activated successfully.'
            ),
        )

    else:

        messages.warning(
            request,
            (
                f'Account "{staff_user.username}" '
                f'was deactivated.'
            ),
        )

    return redirect(
        "manage_staff_accounts"
    )