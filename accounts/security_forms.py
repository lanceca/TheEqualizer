from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm


User = get_user_model()


class ChangeEmailForm(forms.Form):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Enter your current password",
            }
        ),
    )

    new_email = forms.EmailField(
        label="New Email",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "Enter your new email address",
            }
        ),
    )

    confirm_email = forms.EmailField(
        label="Confirm New Email",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "Re-enter your new email address",
            }
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data.get(
            "current_password",
            "",
        )

        if not self.user.check_password(
            password
        ):
            raise forms.ValidationError(
                "Your current password is incorrect."
            )

        return password

    def clean_new_email(self):
        email = (
            self.cleaned_data.get(
                "new_email",
                "",
            )
            .strip()
            .lower()
        )

        if not email:
            raise forms.ValidationError(
                "Email address is required."
            )

        if (
            self.user.email
            and self.user.email.lower() == email
        ):
            raise forms.ValidationError(
                "This is already your current email address."
            )

        if (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=self.user.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "This email address is already associated with another account."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        new_email = cleaned_data.get(
            "new_email"
        )
        confirm_email = (
            cleaned_data.get(
                "confirm_email",
                "",
            )
            .strip()
            .lower()
        )

        if (
            new_email
            and confirm_email
            and new_email != confirm_email
        ):
            self.add_error(
                "confirm_email",
                "The email addresses do not match.",
            )

        return cleaned_data

    def save(self):
        self.user.email = self.cleaned_data[
            "new_email"
        ]
        self.user.email_verified = False
        self.user.save(
            update_fields=[
                "email",
                "email_verified",
            ]
        )
        return self.user


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "Enter your account email",
            }
        ),
    )

    def clean_email(self):
        return (
            self.cleaned_data["email"]
            .strip()
            .lower()
        )


class VerifiedPasswordResetForm(
    PasswordResetForm
):
    """
    Password recovery only sends mail for active accounts whose
    email address has already been verified.

    The public response remains identical whether or not a matching
    account exists, preventing account/email enumeration.
    """

    def get_users(self, email):
        email = email.strip().lower()

        users = (
            User._default_manager
            .filter(
                email__iexact=email,
                is_active=True,
                email_verified=True,
            )
        )

        for user in users:
            if user.has_usable_password():
                yield user
