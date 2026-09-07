from django.db import transaction

from .context import get_current_actor
from .models import ActionLog


SENSITIVE_METADATA_KEYS = {
    "password",
    "password1",
    "password2",
    "current_password",
    "new_password",
    "token",
    "reset_token",
    "verification_token",
    "verification_url",
    "api_key",
    "secret",
    "session",
    "sessionid",
    "cookie",
    "csrf",
    "email",
    "old_email",
    "new_email",
}


def _clean_metadata_value(value, key_name=""):
    normalized_key = (
        str(key_name)
        .strip()
        .lower()
    )

    if normalized_key in SENSITIVE_METADATA_KEYS:
        return None

    if isinstance(value, dict):
        cleaned = {}

        for key, item in value.items():
            normalized = (
                str(key)
                .strip()
                .lower()
            )

            if normalized in SENSITIVE_METADATA_KEYS:
                continue

            cleaned[key] = _clean_metadata_value(
                item,
                key,
            )

        return cleaned

    if isinstance(value, (list, tuple, set)):
        return [
            _clean_metadata_value(item)
            for item in value
        ]

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    return str(value)


def sanitize_metadata(metadata):
    if not metadata:
        return {}

    cleaned = _clean_metadata_value(
        metadata
    )

    if not isinstance(cleaned, dict):
        return {}

    return cleaned


def _snapshot_actor(actor):
    if (
        actor is None
        or not getattr(
            actor,
            "is_authenticated",
            False,
        )
    ):
        return None, "", ""

    return (
        actor,
        getattr(actor, "username", "") or "",
        getattr(actor, "role", "") or "",
    )


def _target_details(target):
    if target is None:
        return "", "", ""

    target_type = target.__class__.__name__

    target_id = str(
        getattr(target, "pk", "")
        or ""
    )

    try:
        target_label = str(target)
    except Exception:
        target_label = target_type

    return (
        target_type,
        target_id,
        target_label[:255],
    )


def log_action(
    *,
    action,
    module,
    target=None,
    description="",
    actor=None,
    request=None,
    metadata=None,
    sensitivity=ActionLog.Sensitivity.NORMAL,
):
    """
    Central audit writer.

    Never place passwords, reset tokens, verification links,
    sessions, cookies, API keys, or secrets in the description
    or metadata.
    """

    if actor is None and request is not None:
        request_user = getattr(
            request,
            "user",
            None,
        )

        if (
            request_user is not None
            and getattr(
                request_user,
                "is_authenticated",
                False,
            )
        ):
            actor = request_user

    if actor is None:
        actor = get_current_actor()

    (
        actor_object,
        actor_username,
        actor_role,
    ) = _snapshot_actor(actor)

    (
        target_type,
        target_id,
        target_label,
    ) = _target_details(target)

    safe_metadata = sanitize_metadata(
        metadata
    )

    return ActionLog.objects.create(
        actor=actor_object,
        actor_username_snapshot=actor_username,
        actor_role_snapshot=actor_role,
        action=action,
        module=module,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        description=description or "",
        sensitivity=sensitivity,
        metadata=safe_metadata,
    )


def log_action_on_commit(**kwargs):
    """Write an audit entry only after the DB transaction commits."""

    transaction.on_commit(
        lambda: log_action(**kwargs)
    )
