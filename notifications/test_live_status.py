import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .models import Notification
from .views import notification_status


User = get_user_model()


class NotificationLiveStatusTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="live-status-user",
            password="LiveStatus123!",
            role="SUPER_ADMIN",
        )

    def get_status(self):
        request = self.factory.get(
            "/notifications/status/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = self.user
        return notification_status(request)

    def test_status_returns_fresh_unread_count_and_latest_notification(self):
        first = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.Type.GENERAL,
            message="First activity",
        )
        newest = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.Type.SUBMISSION,
            message="A new submission is ready for review.",
            related_url="/publications/submissions/pending/",
        )

        first.is_read = True
        first.save(update_fields=["is_read"])

        response = self.get_status()
        payload = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["unread_notification_count"], 1)
        self.assertEqual(payload["latest_notification_id"], newest.id)
        self.assertEqual(
            payload["latest_notification"]["message"],
            "A new submission is ready for review.",
        )
        self.assertEqual(
            payload["latest_notification"]["related_url"],
            "/publications/submissions/pending/",
        )
        self.assertIn("no-store", response["Cache-Control"])

    def test_status_changes_without_a_new_page_render(self):
        initial_response = self.get_status()
        initial_payload = json.loads(initial_response.content)

        self.assertEqual(
            initial_payload["unread_notification_count"],
            0,
        )

        notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.Type.GENERAL,
            message="Live update",
        )

        refreshed_response = self.get_status()
        refreshed_payload = json.loads(refreshed_response.content)

        self.assertEqual(
            refreshed_payload["unread_notification_count"],
            1,
        )
        self.assertEqual(
            refreshed_payload["latest_notification_id"],
            notification.id,
        )
