from django.apps import apps
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
)
from django.db.models.signals import (
    m2m_changed,
    post_save,
    pre_delete,
    pre_save,
)

from .models import ActionLog
from .services import log_action


AUDITED_MODELS = {
    "accounts.User": {
        "module": "ACCOUNTS",
        "sensitive": True,
    },
    "publications.Category": {
        "module": "PUBLICATIONS",
    },
    "publications.Tag": {
        "module": "PUBLICATIONS",
    },
    "publications.Article": {
        "module": "PUBLICATIONS",
    },
    "publications.ArticleContributor": {
        "module": "PUBLICATIONS",
    },
    "publications.ArticleAttachment": {
        "module": "PUBLICATIONS",
    },
    "publications.ArticleVideoAttachment": {
        "module": "PUBLICATIONS",
    },
    "publications.Submission": {
        "module": "WORKFLOW",
    },
    "publications.EditRequest": {
        "module": "WORKFLOW",
    },
    "publications.DeletionRequest": {
        "module": "WORKFLOW",
    },
    "publications.ContentReport": {
        "module": "WORKFLOW",
    },
    "publications.DigitalPublication": {
        "module": "MANAGEMENT",
    },
    "publications.SchoolAdvertisement": {
        "module": "MANAGEMENT",
    },
    "publications.AboutUsPage": {
        "module": "MANAGEMENT",
    },
    "publications.PeopleProfile": {
        "module": "MANAGEMENT",
    },
}


IGNORED_FIELDS = {
    "id",
    "pk",
    "created_at",
    "updated_at",
    "uploaded_at",
    "submitted_at",
    "reviewed_at",
    "archived_at",
    "published_at",
    "resolved_at",
    "last_login",
    "password",
    "view_count",
    "reaction_count",
    "share_count",
    "page_count",
    "file_size",
}


def _is_ignored_field(field_name):
    return (
        field_name in IGNORED_FIELDS
        or field_name.startswith(
            "snapshot_"
        )
    )


def _state_for_instance(instance):
    state = {}

    for field in instance._meta.concrete_fields:
        field_name = field.name

        if _is_ignored_field(
            field_name
        ):
            continue

        state[field_name] = getattr(
            instance,
            field.attname,
            None,
        )

    return state


def _changed_fields(before, after):
    return [
        field_name
        for field_name in sorted(
            set(before) | set(after)
        )
        if before.get(field_name)
        != after.get(field_name)
    ]


def _audit_options(instance):
    model_label = (
        f"{instance._meta.app_label}."
        f"{instance.__class__.__name__}"
    )

    return AUDITED_MODELS.get(
        model_label
    )


def _sensitivity(options):
    if (
        options
        and options.get("sensitive")
    ):
        return (
            ActionLog.Sensitivity.SENSITIVE
        )

    return (
        ActionLog.Sensitivity.NORMAL
    )


def _created_action(instance):
    name = instance.__class__.__name__

    mapping = {
        "User": (
            "ACCOUNT_CREATED",
            "Created account",
        ),
        "Category": (
            "CATEGORY_CREATED",
            "Created publication category",
        ),
        "Tag": (
            "TAG_CREATED",
            "Created publication tag",
        ),
        "Article": (
            "ARTICLE_CREATED",
            "Created article",
        ),
        "ArticleContributor": (
            "ARTICLE_CONTRIBUTOR_ADDED",
            "Added article contributor",
        ),
        "ArticleAttachment": (
            "ARTICLE_ATTACHMENT_ADDED",
            "Added article image attachment",
        ),
        "ArticleVideoAttachment": (
            "ARTICLE_VIDEO_ADDED",
            "Added article video attachment",
        ),
        "Submission": (
            "SUBMISSION_CREATED",
            "Submitted article for review",
        ),
        "EditRequest": (
            "EDIT_REQUEST_CREATED",
            "Created edit request",
        ),
        "DeletionRequest": (
            "DELETION_REQUEST_CREATED",
            "Created deletion request",
        ),
        "ContentReport": (
            "CONTENT_REPORT_CREATED",
            "Created content report",
        ),
        "DigitalPublication": (
            "DIGITAL_PUBLICATION_CREATED",
            "Created digital publication",
        ),
        "SchoolAdvertisement": (
            "ADVERTISEMENT_CREATED",
            "Created homepage advertisement",
        ),
        "AboutUsPage": (
            "ABOUT_US_CREATED",
            "Created About Us page",
        ),
        "PeopleProfile": (
            "PEOPLE_PROFILE_CREATED",
            "Created People & Teams profile",
        ),
    }

    return mapping.get(
        name,
        (
            f"{name.upper()}_CREATED",
            f"Created {name}",
        ),
    )


def _updated_action(
    instance,
    changed_fields,
):
    name = instance.__class__.__name__

    if name == "User":
        if "email" in changed_fields:
            return (
                "ACCOUNT_EMAIL_CHANGED",
                "Changed account email address",
            )

        if (
            "email_verified"
            in changed_fields
        ):
            return (
                "ACCOUNT_EMAIL_VERIFICATION_CHANGED",
                "Changed account email verification state",
            )

        if "role" in changed_fields:
            return (
                "ACCOUNT_ROLE_CHANGED",
                "Changed account role",
            )

        if "is_active" in changed_fields:
            active = bool(
                getattr(
                    instance,
                    "is_active",
                    False,
                )
            )

            return (
                (
                    "ACCOUNT_ACTIVATED"
                    if active
                    else "ACCOUNT_DEACTIVATED"
                ),
                (
                    "Activated account"
                    if active
                    else "Deactivated account"
                ),
            )

        return (
            "ACCOUNT_UPDATED",
            "Updated account",
        )

    if name == "Article":
        if (
            "is_archived"
            in changed_fields
        ):
            archived = bool(
                getattr(
                    instance,
                    "is_archived",
                    False,
                )
            )

            return (
                (
                    "ARTICLE_ARCHIVED"
                    if archived
                    else "ARTICLE_RESTORED"
                ),
                (
                    "Archived article"
                    if archived
                    else "Restored article from archive"
                ),
            )

        if (
            "is_published"
            in changed_fields
        ):
            published = bool(
                getattr(
                    instance,
                    "is_published",
                    False,
                )
            )

            return (
                (
                    "ARTICLE_PUBLISHED"
                    if published
                    else "ARTICLE_UNPUBLISHED"
                ),
                (
                    "Published article"
                    if published
                    else "Unpublished article"
                ),
            )

        return (
            "ARTICLE_UPDATED",
            "Updated article",
        )

    status = getattr(
        instance,
        "status",
        None,
    )

    if (
        "status" in changed_fields
        and status
    ):
        status_name = str(
            status
        ).upper()

        prefix_map = {
            "Submission": "SUBMISSION",
            "EditRequest": "EDIT_REQUEST",
            "DeletionRequest": "DELETION_REQUEST",
            "ContentReport": "CONTENT_REPORT",
            "DigitalPublication": "DIGITAL_PUBLICATION",
        }

        readable_map = {
            "Submission": "submission",
            "EditRequest": "edit request",
            "DeletionRequest": "deletion request",
            "ContentReport": "content report",
            "DigitalPublication": "digital publication",
        }

        if name in prefix_map:
            return (
                (
                    f"{prefix_map[name]}_"
                    f"{status_name}"
                ),
                (
                    f"Changed {readable_map[name]} "
                    f"status to "
                    f"{status_name.replace('_', ' ').title()}"
                ),
            )

    if (
        name == "SchoolAdvertisement"
        and "is_active"
        in changed_fields
    ):
        active = bool(
            getattr(
                instance,
                "is_active",
                False,
            )
        )

        return (
            (
                "ADVERTISEMENT_ACTIVATED"
                if active
                else "ADVERTISEMENT_DEACTIVATED"
            ),
            (
                "Activated homepage advertisement"
                if active
                else "Deactivated homepage advertisement"
            ),
        )

    if (
        name == "AboutUsPage"
        and "is_published"
        in changed_fields
    ):
        published = bool(
            getattr(
                instance,
                "is_published",
                False,
            )
        )

        return (
            (
                "ABOUT_US_PUBLISHED"
                if published
                else "ABOUT_US_UNPUBLISHED"
            ),
            (
                "Published About Us page"
                if published
                else "Unpublished About Us page"
            ),
        )

    if (
        name == "PeopleProfile"
        and "is_active"
        in changed_fields
    ):
        active = bool(
            getattr(
                instance,
                "is_active",
                False,
            )
        )

        return (
            (
                "PEOPLE_PROFILE_ACTIVATED"
                if active
                else "PEOPLE_PROFILE_DEACTIVATED"
            ),
            (
                "Activated People & Teams profile"
                if active
                else "Deactivated People & Teams profile"
            ),
        )

    mapping = {
        "Category": (
            "CATEGORY_UPDATED",
            "Updated publication category",
        ),
        "Tag": (
            "TAG_UPDATED",
            "Updated publication tag",
        ),
        "ArticleContributor": (
            "ARTICLE_CONTRIBUTOR_UPDATED",
            "Updated article contributor",
        ),
        "ArticleAttachment": (
            "ARTICLE_ATTACHMENT_UPDATED",
            "Updated article image attachment",
        ),
        "ArticleVideoAttachment": (
            "ARTICLE_VIDEO_UPDATED",
            "Updated article video attachment",
        ),
        "DigitalPublication": (
            "DIGITAL_PUBLICATION_UPDATED",
            "Updated digital publication",
        ),
        "SchoolAdvertisement": (
            "ADVERTISEMENT_UPDATED",
            "Updated homepage advertisement",
        ),
        "AboutUsPage": (
            "ABOUT_US_UPDATED",
            "Updated About Us page",
        ),
        "PeopleProfile": (
            "PEOPLE_PROFILE_UPDATED",
            "Updated People & Teams profile",
        ),
    }

    return mapping.get(
        name,
        (
            f"{name.upper()}_UPDATED",
            f"Updated {name}",
        ),
    )


def _delete_action(instance):
    name = instance.__class__.__name__

    mapping = {
        "User": (
            "ACCOUNT_DELETED",
            "Deleted account",
        ),
        "Category": (
            "CATEGORY_DELETED",
            "Deleted publication category",
        ),
        "Tag": (
            "TAG_DELETED",
            "Deleted publication tag",
        ),
        "Article": (
            "ARTICLE_DELETED",
            "Permanently deleted article",
        ),
        "ArticleContributor": (
            "ARTICLE_CONTRIBUTOR_REMOVED",
            "Removed article contributor",
        ),
        "ArticleAttachment": (
            "ARTICLE_ATTACHMENT_REMOVED",
            "Removed article image attachment",
        ),
        "ArticleVideoAttachment": (
            "ARTICLE_VIDEO_REMOVED",
            "Removed article video attachment",
        ),
        "Submission": (
            "SUBMISSION_DELETED",
            "Deleted submission",
        ),
        "EditRequest": (
            "EDIT_REQUEST_DELETED",
            "Deleted edit request",
        ),
        "DeletionRequest": (
            "DELETION_REQUEST_DELETED",
            "Deleted deletion request",
        ),
        "ContentReport": (
            "CONTENT_REPORT_DELETED",
            "Deleted content report",
        ),
        "DigitalPublication": (
            "DIGITAL_PUBLICATION_DELETED",
            "Deleted digital publication",
        ),
        "SchoolAdvertisement": (
            "ADVERTISEMENT_DELETED",
            "Deleted homepage advertisement",
        ),
        "AboutUsPage": (
            "ABOUT_US_DELETED",
            "Deleted About Us page",
        ),
        "PeopleProfile": (
            "PEOPLE_PROFILE_DELETED",
            "Deleted People & Teams profile",
        ),
    }

    return mapping.get(
        name,
        (
            f"{name.upper()}_DELETED",
            f"Deleted {name}",
        ),
    )


def _capture_previous_state(
    sender,
    instance,
    **kwargs,
):
    options = _audit_options(
        instance
    )

    if not options:
        return

    if not getattr(
        instance,
        "pk",
        None,
    ):
        instance._audit_previous_state = {}
        return

    previous = (
        sender.objects
        .filter(pk=instance.pk)
        .first()
    )

    if previous is None:
        instance._audit_previous_state = {}
        return

    instance._audit_previous_state = (
        _state_for_instance(previous)
    )


def _log_saved_model(
    sender,
    instance,
    created,
    **kwargs,
):
    options = _audit_options(
        instance
    )

    if not options:
        return

    sensitivity = _sensitivity(
        options
    )

    if created:
        action, description = (
            _created_action(instance)
        )

        log_action(
            action=action,
            module=options["module"],
            target=instance,
            description=description,
            sensitivity=sensitivity,
        )

        return

    before = getattr(
        instance,
        "_audit_previous_state",
        {},
    )

    after = _state_for_instance(
        instance
    )

    changed_fields = _changed_fields(
        before,
        after,
    )

    if not changed_fields:
        return

    action, description = (
        _updated_action(
            instance,
            changed_fields,
        )
    )

    log_action(
        action=action,
        module=options["module"],
        target=instance,
        description=description,
        metadata={
            "changed_fields": changed_fields,
        },
        sensitivity=sensitivity,
    )


def _log_deleted_model(
    sender,
    instance,
    **kwargs,
):
    options = _audit_options(
        instance
    )

    if not options:
        return

    action, description = (
        _delete_action(instance)
    )

    log_action(
        action=action,
        module=options["module"],
        target=instance,
        description=description,
        sensitivity=_sensitivity(
            options
        ),
    )


def _log_login(
    sender,
    request,
    user,
    **kwargs,
):
    log_action(
        action="USER_LOGGED_IN",
        module="SECURITY",
        target=user,
        actor=user,
        request=request,
        description=(
            "Signed in to The Equalizer"
        ),
        sensitivity=(
            ActionLog.Sensitivity.SENSITIVE
        ),
    )


def _log_logout(
    sender,
    request,
    user,
    **kwargs,
):
    log_action(
        action="USER_LOGGED_OUT",
        module="SECURITY",
        target=user,
        actor=user,
        request=request,
        description=(
            "Signed out of The Equalizer"
        ),
        sensitivity=(
            ActionLog.Sensitivity.SENSITIVE
        ),
    )


def _log_article_tags(
    sender,
    instance,
    action,
    reverse,
    model,
    pk_set,
    **kwargs,
):
    if action not in {
        "post_add",
        "post_remove",
        "post_clear",
    }:
        return

    log_action(
        action="ARTICLE_TAGS_CHANGED",
        module="PUBLICATIONS",
        target=instance,
        description="Updated article tags",
        metadata={
            "operation": action,
            "affected_count": (
                len(pk_set)
                if pk_set
                else 0
            ),
        },
    )


_registered = False


def register_audit_signals():
    global _registered

    if _registered:
        return

    _registered = True

    for model_label in AUDITED_MODELS:
        try:
            model = apps.get_model(
                model_label
            )
        except LookupError:
            continue

        pre_save.connect(
            _capture_previous_state,
            sender=model,
            weak=False,
            dispatch_uid=(
                f"audit_pre_save_"
                f"{model_label}"
            ),
        )

        post_save.connect(
            _log_saved_model,
            sender=model,
            weak=False,
            dispatch_uid=(
                f"audit_post_save_"
                f"{model_label}"
            ),
        )

        pre_delete.connect(
            _log_deleted_model,
            sender=model,
            weak=False,
            dispatch_uid=(
                f"audit_pre_delete_"
                f"{model_label}"
            ),
        )

    user_logged_in.connect(
        _log_login,
        weak=False,
        dispatch_uid=(
            "audit_user_logged_in"
        ),
    )

    user_logged_out.connect(
        _log_logout,
        weak=False,
        dispatch_uid=(
            "audit_user_logged_out"
        ),
    )

    try:
        article_model = apps.get_model(
            "publications.Article"
        )

        m2m_changed.connect(
            _log_article_tags,
            sender=article_model.tags.through,
            weak=False,
            dispatch_uid=(
                "audit_article_tags_changed"
            ),
        )

    except LookupError:
        pass
