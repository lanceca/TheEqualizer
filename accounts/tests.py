from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .security_forms import (
    ChangeEmailForm,
)


User = get_user_model()


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends."
        "locmem.EmailBackend"
    ),
    SITE_URL="http://testserver",
)
class EmailSecurityTests(TestCase):

    def create_user(
        self,
        *,
        username="editor1",
        email="editor1@example.com",
        verified=False,
    ):
        user = User.objects.create_user(
            username=username,
            email=email,
            password="A-Strong-Test-Pass-987!",
            role=User.Role.EDITOR,
        )

        if verified:
            user.email_verified = True
            user.save(
                update_fields=[
                    "email_verified",
                ]
            )

        return user

    def test_email_is_normalized(self):
        user = self.create_user(
            email="Editor1@Example.COM",
        )

        self.assertEqual(
            user.email,
            "editor1@example.com",
        )

    def test_new_account_sends_verification_email(self):

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            self.create_user()

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        self.assertIn(
            "/verify-email/",
            mail.outbox[0].body,
        )

    def test_unverified_user_cannot_authenticate(self):
        self.create_user(
            verified=False,
        )

        user = authenticate(
            username="editor1",
            password="A-Strong-Test-Pass-987!",
        )

        self.assertIsNone(user)

    def test_verified_user_can_authenticate(self):
        self.create_user(
            verified=True,
        )

        user = authenticate(
            username="editor1",
            password="A-Strong-Test-Pass-987!",
        )

        self.assertIsNotNone(user)

    def test_duplicate_email_rejected_by_database(self):
        self.create_user(
            username="first",
            email="same@example.com",
        )

        with self.assertRaises(Exception):
            self.create_user(
                username="second",
                email="same@example.com",
            )

    def test_change_email_requires_password(self):
        user = self.create_user(
            verified=True,
        )

        form = ChangeEmailForm(
            {
                "current_password": "wrong",
                "new_email": "new@example.com",
                "confirm_email": "new@example.com",
            },
            user=user,
        )

        self.assertFalse(
            form.is_valid()
        )

    def test_password_reset_does_not_email_unverified_user(self):
        self.create_user(
            verified=False,
        )

        mail.outbox.clear()

        response = self.client.post(
            reverse(
                "password_reset"
            ),
            {
                "email": "editor1@example.com",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            len(mail.outbox),
            0,
        )

    def test_password_reset_emails_verified_user(self):
        self.create_user(
            verified=True,
        )

        mail.outbox.clear()

        response = self.client.post(
            reverse(
                "password_reset"
            ),
            {
                "email": "editor1@example.com",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )
