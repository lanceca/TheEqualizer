from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
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
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
