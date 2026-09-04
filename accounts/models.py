from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from PIL import Image, UnidentifiedImageError


def validate_profile_picture(uploaded_file):
    """
    Validate staff profile pictures by size, extension, real image
    format, and image integrity.
    """

    if not uploaded_file:
        return

    max_size = 5 * 1024 * 1024
    allowed_extensions = {
        "jpg",
        "jpeg",
        "png",
        "webp",
    }
    allowed_formats = {
        "JPEG",
        "PNG",
        "WEBP",
    }

    if (
        getattr(uploaded_file, "size", 0)
        > max_size
    ):
        raise ValidationError(
            "Profile picture cannot exceed 5 MB."
        )

    extension = (
        Path(
            getattr(
                uploaded_file,
                "name",
                "",
            )
        )
        .suffix
        .lower()
        .lstrip(".")
    )

    if extension not in allowed_extensions:
        raise ValidationError(
            (
                "Unsupported profile picture type. "
                "Use JPG, JPEG, PNG, or WEBP."
            )
        )

    original_position = 0

    try:

        if hasattr(
            uploaded_file,
            "tell",
        ):
            original_position = (
                uploaded_file.tell()
            )

        uploaded_file.seek(0)

        image = Image.open(
            uploaded_file
        )

        if image.format not in allowed_formats:
            raise ValidationError(
                (
                    "Unsupported profile picture format. "
                    "Use JPG, PNG, or WEBP."
                )
            )

        width, height = image.size

        if (
            width <= 0
            or height <= 0
        ):
            raise ValidationError(
                "Profile picture has invalid dimensions."
            )

        if (
            width * height
            > 25_000_000
        ):
            raise ValidationError(
                (
                    "Profile picture resolution is too large. "
                    "Please upload a smaller image."
                )
            )

        image.verify()

    except ValidationError:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as error:
        raise ValidationError(
            (
                "The uploaded profile picture is not "
                "a valid or readable image."
            )
        ) from error

    finally:

        try:
            uploaded_file.seek(
                original_position
            )

        except (
            AttributeError,
            OSError,
            ValueError,
        ):
            pass


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin"
        ADVISER = "ADVISER", "Adviser"
        EIC = "EIC", "Editor in Chief"
        EDITOR = "EDITOR", "Editor"
        STAFF = "STAFF", "Staff"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )


    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        validators=[
            validate_profile_picture,
        ],
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.username