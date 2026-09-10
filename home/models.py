from django.db import models


class MobileAppSettings(models.Model):
    """
    Singleton settings row for the public Android app download and
    optional homepage update notice.

    The APK itself should live on GitHub Releases (or another HTTPS
    release host). The website stores only the current public download URL,
    which avoids Render's ephemeral filesystem and Supabase's per-file
    upload limits.
    """

    current_version = models.CharField(
        max_length=30,
        blank=True,
    )

    download_url = models.URLField(
        max_length=600,
        blank=True,
    )

    notice_enabled = models.BooleanField(
        default=False,
    )

    notice_title = models.CharField(
        max_length=140,
        default="A new version of The Equalizer app is available.",
    )

    notice_message = models.TextField(
        max_length=500,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Mobile app settings"
        verbose_name_plural = "Mobile app settings"

    def __str__(self):
        if self.current_version:
            return f"The Equalizer App {self.current_version}"

        return "The Equalizer App Settings"

    def save(self, *args, **kwargs):
        # Keep this table as a true singleton.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(
            pk=1,
        )
        return settings
