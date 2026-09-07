from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    logout,
)
from django.contrib.auth.decorators import (
    login_required,
)
from django.contrib.auth.tokens import (
    default_token_generator,
)
from django.shortcuts import (
    redirect,
    render,
)
from django.utils.encoding import force_str
from django.utils.http import (
    urlsafe_base64_decode,
)

from .email_utils import (
    send_verification_email,
)
from .security_forms import (
    ChangeEmailForm,
    ResendVerificationForm,
)


User = get_user_model()


def verification_pending(request):
    return render(
        request,
        "accounts/"
        "verification_pending.html",
    )


def verify_email(
    request,
    uidb64,
    token,
):
    user = None

    try:
        user_id = force_str(
            urlsafe_base64_decode(
                uidb64
            )
        )

        user = User.objects.get(
            pk=user_id
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
    ):
        user = None

    if (
        user is not None
        and user.email
        and default_token_generator.check_token(
            user,
            token,
        )
    ):
        if not user.email_verified:
            user.email_verified = True
            user.save(
                update_fields=[
                    "email_verified",
                ]
            )

        messages.success(
            request,
            (
                "Your email address has been verified. "
                "You can now sign in."
            ),
        )

        return redirect(
            "login"
        )

    return render(
        request,
        "accounts/"
        "verification_invalid.html",
        status=400,
    )


def resend_verification(request):
    sent = False

    if request.method == "POST":
        form = ResendVerificationForm(
            request.POST
        )

        if form.is_valid():
            email = form.cleaned_data[
                "email"
            ]

            user = (
                User.objects
                .filter(
                    email__iexact=email,
                    is_active=True,
                    email_verified=False,
                )
                .first()
            )

            if user:
                sent = (
                    send_verification_email(
                        user
                    )
                )

            # Always use the same public message whether a user exists,
            # is already verified, or delivery failed.
            return render(
                request,
                "accounts/"
                "verification_resend_done.html",
                {
                    "delivery_attempted": (
                        sent
                    ),
                },
            )

    else:
        form = (
            ResendVerificationForm()
        )

    return render(
        request,
        "accounts/"
        "verification_resend.html",
        {
            "form": form,
        },
    )


@login_required
def change_email(request):
    if request.method == "POST":
        form = ChangeEmailForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            user = form.save()

            # The model invalidates verification and the post_save
            # signal sends the new verification message.
            logout(request)

            messages.info(
                request,
                (
                    "Your email address was changed. "
                    "Verify the new address before signing in again."
                ),
            )

            return redirect(
                "verification_pending"
            )

    else:
        form = ChangeEmailForm(
            user=request.user
        )

    return render(
        request,
        "accounts/change_email.html",
        {
            "form": form,
        },
    )
