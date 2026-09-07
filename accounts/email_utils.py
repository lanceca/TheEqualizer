import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


logger = logging.getLogger(__name__)


def build_verification_url(user):
    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )

    token = (
        default_token_generator
        .make_token(user)
    )

    path = reverse(
        "verify_email",
        kwargs={
            "uidb64": uid,
            "token": token,
        },
    )

    return (
        f"{settings.SITE_URL.rstrip('/')}"
        f"{path}"
    )


def send_verification_email(user):
    if (
        not user.email
        or user.email_verified
        or not user.is_active
    ):
        return False

    verification_url = (
        build_verification_url(user)
    )

    context = {
        "user": user,
        "verification_url": (
            verification_url
        ),
    }

    subject = render_to_string(
        "accounts/emails/"
        "verification_subject.txt",
        context,
    ).strip()

    message = render_to_string(
        "accounts/emails/"
        "verification_email.txt",
        context,
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=(
                settings.DEFAULT_FROM_EMAIL
            ),
            recipient_list=[
                user.email,
            ],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Unable to send verification email for user id %s.",
            user.pk,
        )
        return False

    return True
