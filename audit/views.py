from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import ActionLog


ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "ADVISER",
    "EIC",
    "EDITOR",
    "STAFF",
}


FULL_VISIBILITY_ROLES = {
    "SUPER_ADMIN",
    "ADMIN",
    "ADVISER",
}


def _can_view_audit(user):
    return (
        getattr(
            user,
            "is_authenticated",
            False,
        )
        and getattr(
            user,
            "role",
            "",
        )
        in ALLOWED_ROLES
    )


def _parse_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _filtered_queryset(request):
    queryset = (
        ActionLog.objects
        .select_related("actor")
        .all()
    )

    search_text = (
        request.GET.get("q", "")
        .strip()[:120]
    )

    role = (
        request.GET.get("role", "")
        .strip()[:30]
    )

    module = (
        request.GET.get("module", "")
        .strip()[:50]
    )

    action = (
        request.GET.get("action", "")
        .strip()[:80]
    )

    date_from_value = (
        request.GET.get(
            "date_from",
            "",
        )
        .strip()
    )

    date_to_value = (
        request.GET.get(
            "date_to",
            "",
        )
        .strip()
    )

    date_from = _parse_date(
        date_from_value
    )

    date_to = _parse_date(
        date_to_value
    )

    if search_text:
        queryset = queryset.filter(
            Q(
                actor_username_snapshot__icontains=search_text
            )
            | Q(
                action__icontains=search_text
            )
            | Q(
                module__icontains=search_text
            )
            | Q(
                target_type__icontains=search_text
            )
            | Q(
                target_label__icontains=search_text
            )
            | Q(
                description__icontains=search_text
            )
        )

    if role:
        queryset = queryset.filter(
            actor_role_snapshot=role
        )

    if module:
        queryset = queryset.filter(
            module=module
        )

    if action:
        queryset = queryset.filter(
            action=action
        )

    if date_from:
        queryset = queryset.filter(
            created_at__date__gte=date_from
        )

    if date_to:
        queryset = queryset.filter(
            created_at__date__lte=date_to
        )

    filters = {
        "q": search_text,
        "role": role,
        "module": module,
        "action": action,
        "date_from": date_from_value,
        "date_to": date_to_value,
    }

    return queryset, filters


def _filter_options():
    return {
        "roles": list(
            ActionLog.objects
            .exclude(
                actor_role_snapshot=""
            )
            .order_by(
                "actor_role_snapshot"
            )
            .values_list(
                "actor_role_snapshot",
                flat=True,
            )
            .distinct()
        ),
        "modules": list(
            ActionLog.objects
            .order_by("module")
            .values_list(
                "module",
                flat=True,
            )
            .distinct()
        ),
        "actions": list(
            ActionLog.objects
            .order_by("action")
            .values_list(
                "action",
                flat=True,
            )
            .distinct()
        ),
    }


def _serialize_log(log, user):
    full_visibility = (
        getattr(
            user,
            "role",
            "",
        )
        in FULL_VISIBILITY_ROLES
    )

    sensitive = (
        log.sensitivity
        == ActionLog.Sensitivity.SENSITIVE
    )

    if sensitive and not full_visibility:
        description = (
            "Sensitive account/security action recorded."
        )
        metadata = {}
        target_label = (
            "Protected account activity"
        )

    else:
        description = log.description
        metadata = log.metadata
        target_label = (
            log.target_label
        )

    return {
        "id": log.id,
        "actor": (
            log.actor_username_snapshot
            or "System"
        ),
        "actor_role": (
            log.actor_role_snapshot
            or "SYSTEM"
        ),
        "action": log.action,
        "module": log.module,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "target_label": target_label,
        "description": description,
        "metadata": metadata,
        "sensitive": sensitive,
        "created_at": (
            log.created_at.isoformat()
        ),
        "created_at_display": (
            timezone.localtime(
                log.created_at
            ).strftime(
                "%b %d, %Y %I:%M %p"
            )
        ),
    }


@never_cache
@login_required
def action_log_view(request):
    if not _can_view_audit(
        request.user
    ):
        return HttpResponseForbidden(
            "You do not have permission to view the action log."
        )

    queryset, filters = (
        _filtered_queryset(request)
    )

    paginator = Paginator(
        queryset,
        50,
    )

    page = paginator.get_page(
        request.GET.get("page", 1)
    )

    rows = [
        _serialize_log(
            log,
            request.user,
        )
        for log in page.object_list
    ]

    context = {
        "audit_rows": rows,
        "audit_page": page,
        "audit_filters": filters,
        "audit_filter_options": (
            _filter_options()
        ),
        "audit_full_visibility": (
            getattr(
                request.user,
                "role",
                "",
            )
            in FULL_VISIBILITY_ROLES
        ),
    }

    return render(
        request,
        "audit/action_log.html",
        context,
    )


@never_cache
@login_required
def action_log_data(request):
    if not _can_view_audit(
        request.user
    ):
        return JsonResponse(
            {
                "detail": (
                    "You do not have permission to view the action log."
                )
            },
            status=403,
        )

    queryset, filters = (
        _filtered_queryset(request)
    )

    paginator = Paginator(
        queryset,
        50,
    )

    page = paginator.get_page(
        request.GET.get("page", 1)
    )

    return JsonResponse(
        {
            "results": [
                _serialize_log(
                    log,
                    request.user,
                )
                for log
                in page.object_list
            ],
            "filters": filters,
            "filter_options": (
                _filter_options()
            ),
            "pagination": {
                "page": page.number,
                "pages": (
                    paginator.num_pages
                ),
                "count": (
                    paginator.count
                ),
                "has_next": (
                    page.has_next()
                ),
                "has_previous": (
                    page.has_previous()
                ),
            },
            "full_visibility": (
                getattr(
                    request.user,
                    "role",
                    "",
                )
                in FULL_VISIBILITY_ROLES
            ),
        }
    )
