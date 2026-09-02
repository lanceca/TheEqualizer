from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_article_image(uploaded_file):
    """
    Validate uploaded article images using:

    - file size
    - filename extension
    - actual image format
    - extension/format consistency
    - image integrity
    - maximum pixel count

    This protects featured images and article attachments.
    """

    if not uploaded_file:
        return

    max_size = getattr(
        settings,
        "ARTICLE_IMAGE_MAX_SIZE",
        8 * 1024 * 1024,
    )

    allowed_extensions = set(
        getattr(
            settings,
            "ARTICLE_ALLOWED_IMAGE_EXTENSIONS",
            [
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
        )
    )

    allowed_formats = set(
        getattr(
            settings,
            "ARTICLE_ALLOWED_IMAGE_FORMATS",
            [
                "JPEG",
                "PNG",
                "WEBP",
            ],
        )
    )

    max_pixels = getattr(
        settings,
        "ARTICLE_IMAGE_MAX_PIXELS",
        40_000_000,
    )

    # ======================================================
    # FILE SIZE
    # ======================================================

    file_size = getattr(
        uploaded_file,
        "size",
        None,
    )

    if (
        file_size is not None
        and file_size > max_size
    ):
        max_size_mb = (
            max_size / 1024 / 1024
        )

        raise ValidationError(
            (
                "Image file is too large. "
                f"The maximum allowed size is "
                f"{max_size_mb:.0f} MB."
            )
        )

    # ======================================================
    # FILE EXTENSION
    # ======================================================

    filename = getattr(
        uploaded_file,
        "name",
        "",
    )

    extension = (
        Path(filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    if extension not in allowed_extensions:

        allowed_display = ", ".join(
            sorted(allowed_extensions)
        )

        raise ValidationError(
            (
                "Unsupported image type. "
                "Allowed extensions are: "
                f"{allowed_display}."
            )
        )

    # ======================================================
    # ACTUAL IMAGE CONTENT
    # ======================================================

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

        actual_format = image.format

        width, height = image.size

        if (
            width <= 0
            or height <= 0
        ):
            raise ValidationError(
                "The uploaded image has invalid dimensions."
            )

        total_pixels = (
            width * height
        )

        if total_pixels > max_pixels:

            raise ValidationError(
                (
                    "Image resolution is too large. "
                    "Please upload a smaller image."
                )
            )

        if actual_format not in allowed_formats:

            raise ValidationError(
                (
                    "Unsupported image format. "
                    "Only JPEG, PNG, and WEBP "
                    "images are allowed."
                )
            )

        # ==================================================
        # EXTENSION / FORMAT MATCH
        # ==================================================

        format_extensions = {
            "JPEG": {
                "jpg",
                "jpeg",
            },
            "PNG": {
                "png",
            },
            "WEBP": {
                "webp",
            },
        }

        valid_extensions = (
            format_extensions.get(
                actual_format,
                set(),
            )
        )

        if (
            valid_extensions
            and extension
            not in valid_extensions
        ):
            raise ValidationError(
                (
                    "The image file extension does not "
                    "match its actual image format."
                )
            )

        # ==================================================
        # IMAGE INTEGRITY
        # ==================================================

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
                "The uploaded file is not a valid "
                "or readable image."
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

def validate_article_video(uploaded_file):
    """
    Validate uploaded article videos using:

    - file size
    - filename extension
    - reported content type
    - basic container signature

    Supported by default: MP4, MOV, WEBM, and M4V.
    """

    if not uploaded_file:
        return

    max_size = getattr(
        settings,
        "ARTICLE_VIDEO_MAX_SIZE",
        250 * 1024 * 1024,
    )

    allowed_extensions = set(
        getattr(
            settings,
            "ARTICLE_ALLOWED_VIDEO_EXTENSIONS",
            [
                "mp4",
                "mov",
                "webm",
                "m4v",
            ],
        )
    )

    allowed_content_types = set(
        getattr(
            settings,
            "ARTICLE_ALLOWED_VIDEO_CONTENT_TYPES",
            [
                "video/mp4",
                "video/quicktime",
                "video/webm",
                "video/x-m4v",
            ],
        )
    )

    file_size = getattr(
        uploaded_file,
        "size",
        None,
    )

    if (
        file_size is not None
        and file_size > max_size
    ):
        max_size_mb = (
            max_size / 1024 / 1024
        )

        raise ValidationError(
            (
                "Video file is too large. "
                "The maximum allowed size is "
                f"{max_size_mb:.0f} MB."
            )
        )

    filename = getattr(
        uploaded_file,
        "name",
        "",
    )

    extension = (
        Path(filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    if extension not in allowed_extensions:
        allowed_display = ", ".join(
            sorted(allowed_extensions)
        )

        raise ValidationError(
            (
                "Unsupported video type. "
                "Allowed extensions are: "
                f"{allowed_display}."
            )
        )

    content_type = (
        getattr(
            uploaded_file,
            "content_type",
            "",
        )
        or ""
    ).lower()

    if (
        content_type
        and content_type not in allowed_content_types
    ):
        raise ValidationError(
            (
                "Unsupported video content type. "
                "Please upload an MP4, MOV, WEBM, "
                "or M4V video."
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
        header = uploaded_file.read(32)

        is_webm = (
            header.startswith(
                b"\x1a\x45\xdf\xa3"
            )
        )

        is_iso_media = (
            len(header) >= 12
            and header[4:8] == b"ftyp"
        )

        if extension == "webm":
            valid_signature = is_webm
        else:
            valid_signature = is_iso_media

        if not valid_signature:
            raise ValidationError(
                (
                    "The uploaded file does not appear "
                    "to be a valid video container for "
                    f".{extension}."
                )
            )

    except ValidationError:
        raise

    except (
        OSError,
        ValueError,
    ) as error:
        raise ValidationError(
            (
                "The uploaded video could not be read."
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

