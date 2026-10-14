from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from home.models import MobileAppSettings

from .models import (
    MobileAppInstallEvent,
    MobileAppInstallThrottle,
)


class MobileAppInstallAnalyticsTests(TestCase):
    def setUp(self):
        self.mobile_settings = (
            MobileAppSettings.get_solo()
        )
        self.mobile_settings.current_version = (
            "1.0.0"
        )
        self.mobile_settings.download_url = (
            "https://example.com/TheEqualizer.apk"
        )
        self.mobile_settings.save()

        self.download_url = reverse(
            "mobile_app_download"
        )

    def click_install(
        self,
        *,
        ip="203.0.113.10",
        user_agent="Equalizer Test Browser",
    ):
        return self.client.get(
            self.download_url,
            REMOTE_ADDR=ip,
            HTTP_USER_AGENT=user_agent,
            HTTP_ACCEPT_LANGUAGE="en-PH",
        )

    def test_first_click_records_event_and_redirects(self):
        response = self.click_install()

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertEqual(
            response["Location"],
            self.mobile_settings.download_url,
        )
        self.assertEqual(
            MobileAppInstallEvent.objects.count(),
            1,
        )
        self.assertEqual(
            MobileAppInstallThrottle.objects.count(),
            1,
        )

    def test_repeat_click_within_30_days_is_not_counted(self):
        self.click_install()
        self.click_install()

        self.assertEqual(
            MobileAppInstallEvent.objects.count(),
            1,
        )

    def test_same_fingerprint_after_30_days_counts_again(self):
        self.click_install()

        throttle = (
            MobileAppInstallThrottle.objects.get()
        )
        throttle.last_counted_at = (
            timezone.now()
            - timedelta(days=31)
        )
        throttle.save(
            update_fields=[
                "last_counted_at",
            ]
        )

        self.click_install()

        self.assertEqual(
            MobileAppInstallEvent.objects.count(),
            2,
        )

    def test_different_fingerprint_counts_separately(self):
        self.click_install(
            ip="203.0.113.10",
        )
        self.click_install(
            ip="203.0.113.11",
        )

        self.assertEqual(
            MobileAppInstallEvent.objects.count(),
            2,
        )

    def test_missing_download_url_does_not_record_event(self):
        self.mobile_settings.download_url = ""
        self.mobile_settings.save()

        response = self.click_install()

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertEqual(
            MobileAppInstallEvent.objects.count(),
            0,
        )
        self.assertEqual(
            MobileAppInstallThrottle.objects.count(),
            0,
        )
