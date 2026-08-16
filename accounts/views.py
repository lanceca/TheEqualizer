from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render


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

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


@login_required
def dashboard_redirect(request):
    """
    Send the authenticated user to the dashboard
    corresponding to their role.
    """

    role = request.user.role

    if role == "SUPER_ADMIN":
        return redirect("super_admin_dashboard")

    elif role == "ADMIN":
        return redirect("admin_dashboard")

    elif role == "ADVISER":
        return redirect("adviser_dashboard")

    elif role == "EIC":
        return redirect("eic_dashboard")

    elif role == "EDITOR":
        return redirect("editor_dashboard")

    elif role == "STAFF":
        return redirect("staff_dashboard")

    return HttpResponseForbidden(
        "Your account does not have a valid role."
    )


@role_required("SUPER_ADMIN")
def super_admin_dashboard(request):
    return render(request, "accounts/dashboards/super_admin.html")


@role_required("ADMIN")
def admin_dashboard(request):
    return render(request, "accounts/dashboards/admin.html")


@role_required("ADVISER")
def adviser_dashboard(request):
    return render(request, "accounts/dashboards/adviser.html")


@role_required("EIC")
def eic_dashboard(request):
    return render(request, "accounts/dashboards/eic.html")


@role_required("EDITOR")
def editor_dashboard(request):
    return render(request, "accounts/dashboards/editor.html")


@role_required("STAFF")
def staff_dashboard(request):
    return render(request, "accounts/dashboards/staff.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        return render(
            request,
            "accounts/login.html",
            {
                "error": "Invalid username or password.",
            },
        )

    return render(request, "accounts/login.html")

def logout_view(request):
    logout(request)
    return redirect("home")