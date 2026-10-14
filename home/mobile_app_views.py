from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_POST

from analytics.models import (
    MobileAppInstallEvent,
    MobileAppInstallThrottle,
)

from .forms import MobileAppSettingsForm
from .models import MobileAppSettings


MOBILE_APP_INSTALL_ANALYTICS_COOLDOWN = timedelta(days=30)


def _mobile_app_client_ip(request):
    """Return the reader-facing IP without persisting the raw value."""

    forwarded_for = (
        request.META.get(
            "HTTP_X_FORWARDED_FOR",
            "",
        )
        or ""
    )

    if forwarded_for:
        return (
            forwarded_for
            .split(",", 1)[0]
            .strip()
        )[:128]

    return (
        request.META.get(
            "REMOTE_ADDR",
            "",
        )
        or ""
    ).strip()[:128]


def _mobile_app_install_fingerprint(request):
    """
    Build a privacy-preserving browser/device fingerprint for install analytics.

    The raw IP address and browser headers are used only while creating the
    keyed digest and are never saved to the database.
    """

    fingerprint_source = "\n".join(
        [
            _mobile_app_client_ip(request),
            (
                request.META.get(
                    "HTTP_USER_AGENT",
                    "",
                )
                or ""
            )[:512],
            (
                request.META.get(
                    "HTTP_ACCEPT_LANGUAGE",
                    "",
                )
                or ""
            )[:128],
            (
                request.META.get(
                    "HTTP_SEC_CH_UA_PLATFORM",
                    "",
                )
                or ""
            )[:128],
            (
                request.META.get(
                    "HTTP_SEC_CH_UA_MOBILE",
                    "",
                )
                or ""
            )[:32],
        ]
    )

    return salted_hmac(
        "equalizer.mobile-app-install",
        fingerprint_source,
        algorithm="sha256",
    ).hexdigest()


def _record_mobile_app_install(request, app_settings):
    """
    Record at most one analytics event per fingerprint every rolling 30 days.

    Duplicate clicks never block the APK redirect; they are simply excluded
    from analytics until the cooldown has elapsed.
    """

    now = timezone.now()
    cutoff = (
        now
        - MOBILE_APP_INSTALL_ANALYTICS_COOLDOWN
    )
    fingerprint_hash = (
        _mobile_app_install_fingerprint(
            request
        )
    )

    with transaction.atomic():
        throttle, created = (
            MobileAppInstallThrottle.objects
            .select_for_update()
            .get_or_create(
                fingerprint_hash=(
                    fingerprint_hash
                ),
                defaults={
                    "last_counted_at": now,
                },
            )
        )

        should_count = (
            created
            or throttle.last_counted_at
            <= cutoff
        )

        if not should_count:
            return False

        if not created:
            throttle.last_counted_at = now
            throttle.save(
                update_fields=[
                    "last_counted_at",
                ]
            )

        MobileAppInstallEvent.objects.create(
            fingerprint_hash=(
                fingerprint_hash
            ),
            app_version=(
                app_settings.current_version
                or ""
            )[:30],
        )

    return True


def download_mobile_app(request):
    settings = MobileAppSettings.get_solo()

    if not settings.download_url:
        messages.info(
            request,
            "The Android app download is not available yet.",
        )
        return redirect("home")

    _record_mobile_app_install(
        request,
        settings,
    )

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
