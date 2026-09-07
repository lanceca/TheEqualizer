from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .email_utils import (
    send_verification_email,
)


User = get_user_model()


@receiver(
    post_save,
    sender=User,
)
def send_verification_after_email_change(
    sender,
    instance,
    created,
    **kwargs,
):
    should_send = (
        instance.email
        and not instance.email_verified
        and instance.is_active
        and (
            created
            or getattr(
                instance,
                "_email_changed_for_verification",
                False,
            )
        )
    )

    if not should_send:
        return

    transaction.on_commit(
        lambda: send_verification_email(
            instance
        )
    )
