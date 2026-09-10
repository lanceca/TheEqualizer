from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .forms import MobileAppSettingsForm
from .models import MobileAppSettings


def download_mobile_app(request):
    settings = MobileAppSettings.get_solo()

    if not settings.download_url:
        messages.info(
            request,
            "The Android app download is not available yet.",
        )
        return redirect("home")

    return redirect(
        settings.download_url
    )


@login_required
@require_POST
def update_mobile_app_settings(request):
    if getattr(request.user, "role", "") != "SUPER_ADMIN":
        return HttpResponseForbidden(
            "You do not have permission to update mobile app settings."
        )

    settings = MobileAppSettings.get_solo()

    form = MobileAppSettingsForm(
        request.POST,
        instance=settings,
    )

    if form.is_valid():
        form.save()

        messages.success(
            request,
            "Mobile app release settings were updated.",
        )

        return redirect(
            "super_admin_dashboard"
        )

    for field_name, errors in form.errors.items():
        if field_name == "__all__":
            label = "Mobile app settings"
        else:
            field = form.fields.get(field_name)
            label = (
                field.label
                if field is not None
                else field_name.replace("_", " ").title()
            )

        for error in errors:
            messages.error(
                request,
                f"{label}: {error}",
            )

    return redirect(
        "super_admin_dashboard"
    )
