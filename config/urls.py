from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.templatetags.static import static as static_asset
from django.urls import include, path
from django.views.generic.base import RedirectView


urlpatterns = [
    # ======================================================
    # GLOBAL BROWSER ICON FALLBACK
    # ======================================================

    path(
        "favicon.ico",
        RedirectView.as_view(
            url=static_asset(
                "images/favicon.ico"
            ),
            permanent=False,
        ),
        name="favicon",
    ),

    path(
        "admin/",
        admin.site.urls,
    ),

    # ======================================================
    # PUBLIC MOBILE API
    # ======================================================

    path(
        "api/mobile/",
        include("home.mobile_api_urls"),
    ),

    path(
        "",
        include("home.urls"),
    ),

    path(
        "",
        include("accounts.urls"),
    ),

    path(
        "publications/",
        include("publications.urls"),
    ),

    path(
        "notifications/",
        include("notifications.urls"),
    ),

    # ======================================================
    # ACTION / AUDIT LOG
    # ======================================================

    path(
        "activity/",
        include("audit.urls"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
