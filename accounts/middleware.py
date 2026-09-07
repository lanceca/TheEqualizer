from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class VerifiedEmailRequiredMiddleware:
    """
    Prevent an already-authenticated legacy session from bypassing
    the new verification requirement after deployment.
    """

    EXEMPT_PREFIXES = (
        "/login/",
        "/logout/",
        "/verify-email/",
        "/password-reset/",
        "/reset/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(
            request,
            "user",
            None,
        )

        if (
            user
            and user.is_authenticated
            and (
                not user.email
                or not user.email_verified
            )
            and not request.path.startswith(
                self.EXEMPT_PREFIXES
            )
        ):
            logout(request)

            messages.warning(
                request,
                (
                    "Verify your email address "
                    "before accessing the staff portal."
                ),
            )

            return redirect(
                "verification_pending"
            )

        return self.get_response(
            request
        )
