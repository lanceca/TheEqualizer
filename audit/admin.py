from django.contrib import admin

from .models import ActionLog


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "actor_username_snapshot",
        "actor_role_snapshot",
        "action",
        "module",
        "target_type",
        "target_label",
    )

    list_filter = (
        "module",
        "action",
        "actor_role_snapshot",
        "sensitivity",
        "created_at",
    )

    search_fields = (
        "actor_username_snapshot",
        "action",
        "module",
        "target_type",
        "target_label",
        "description",
    )

    ordering = (
        "-created_at",
        "-id",
    )

    readonly_fields = (
        "actor",
        "actor_username_snapshot",
        "actor_role_snapshot",
        "action",
        "module",
        "target_type",
        "target_id",
        "target_label",
        "description",
        "sensitivity",
        "metadata",
        "created_at",
    )

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
