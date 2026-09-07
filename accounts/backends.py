from django.contrib.auth.backends import (
    ModelBackend,
)


class VerifiedEmailModelBackend(
    ModelBackend
):
    """
    Staff authentication succeeds only after the account's email
    address has been verified.
    """

    def user_can_authenticate(self, user):
        return (
            super().user_can_authenticate(
                user
            )
            and bool(user.email)
            and user.email_verified
        )
