from urllib.parse import urlparse

from django import forms

from .models import MobileAppSettings


class MobileAppSettingsForm(forms.ModelForm):
    class Meta:
        model = MobileAppSettings
        fields = [
            "current_version",
            "download_url",
            "notice_enabled",
            "notice_title",
            "notice_message",
        ]

    def clean_download_url(self):
        value = (
            self.cleaned_data.get(
                "download_url",
                "",
            )
            or ""
        ).strip()

        if not value:
            return ""

        parsed = urlparse(value)

        if parsed.scheme != "https":
            raise forms.ValidationError(
                "Use an HTTPS download URL."
            )

        return value

    def clean(self):
        cleaned_data = super().clean()

        if (
            cleaned_data.get("notice_enabled")
            and not cleaned_data.get("download_url")
        ):
            self.add_error(
                "download_url",
                (
                    "Add an APK download URL before enabling "
                    "the homepage update notice."
                ),
            )

        return cleaned_data
