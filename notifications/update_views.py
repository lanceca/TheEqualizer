import re

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from publications.views import publication_role_required
from .forms import SystemUpdateForm
from .models import SystemUpdate, SystemUpdateReceipt
from .updates import pending_updates, visible_updates

staff_required = publication_role_required(*User.Role.values)
manager_required = publication_role_required(User.Role.SUPER_ADMIN)


_CHANGE_NOTE_PATTERN = re.compile(
    r"^\[(New|Fixed|Updated|Removed|Disabled)\]\s*(.*)$",
    re.IGNORECASE,
)


def _change_note_items(change_notes):
    """Return release-note lines in the same categories used by the popup."""
    items = []

    for raw_line in (change_notes or "").splitlines():
        line = raw_line.strip().lstrip("-•").strip()
        if not line:
            continue

        match = _CHANGE_NOTE_PATTERN.match(line)
        if match:
            category = match.group(1).title()
            note = match.group(2).strip()
        else:
            category = "Updated"
            note = line

        if note:
            items.append(
                {
                    "category": category,
                    "category_slug": category.lower(),
                    "text": note,
                }
            )

    return items


def _preview_context(update, target_roles, *, form=None, saved_draft=False):
    return {
        "preview_update": update,
        "preview_target_roles": target_roles,
        "preview_change_items": _change_note_items(update.change_notes),
        "preview_form": form,
        "saved_draft": saved_draft,
    }


@staff_required
def update_history(request):
    return render(request, "notifications/update_history.html", {"updates": visible_updates(request.user)})


@staff_required
def update_detail(request, update_id):
    update = get_object_or_404(visible_updates(request.user), pk=update_id)
    return render(request, "notifications/update_detail.html", {"update": update})


@staff_required
def update_popup(request):
    update = pending_updates(request.user).filter(show_popup=True).first()
    if not update:
        return JsonResponse({"update": None})
    return JsonResponse({"update": {
        "id": update.pk, "title": update.title, "version": update.version,
        "summary": update.summary, "changeNotes": update.change_notes,
        "type": update.get_update_type_display(),
        "published": timezone.localtime(update.published_at).strftime("%b. %d, %Y"),
        "required": update.require_acknowledgement,
        "url": reverse("system_update_detail", args=[update.pk]),
        "ackUrl": reverse("acknowledge_system_update", args=[update.pk]),
    }})


@staff_required
@require_POST
def acknowledge_update(request, update_id):
    update = get_object_or_404(visible_updates(request.user), pk=update_id)
    now = timezone.now()
    with transaction.atomic():
        receipt, _ = SystemUpdateReceipt.objects.get_or_create(update=update, user=request.user)
        SystemUpdateReceipt.objects.filter(pk=receipt.pk).update(seen_at=now, acknowledged_at=now)
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"ok": True})
    return redirect("system_update_history")


@manager_required
def manage_updates(request):
    # Keep unpublished work at the top so the newest draft is always the first
    # item a Super Admin sees. Published releases then follow newest-first.
    drafts = list(
        SystemUpdate.objects
        .filter(is_published=False)
        .order_by("-created_at")
    )
    published = list(
        SystemUpdate.objects
        .filter(is_published=True)
        .order_by("-published_at", "-created_at")
    )

    return render(
        request,
        "notifications/manage_updates.html",
        {
            "updates": drafts + published,
            "draft_count": len(drafts),
            "published_count": len(published),
        },
    )


@manager_required
def update_form(request, update_id=None):
    update = get_object_or_404(SystemUpdate, pk=update_id, is_published=False) if update_id else None
    form = SystemUpdateForm(request.POST or None, instance=update)

    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action", "save")

        if action in {"preview", "edit"}:
            preview_update = form.save(commit=False)
            return render(
                request,
                "notifications/update_preview.html" if action == "preview" else "notifications/update_form.html",
                _preview_context(
                    preview_update,
                    form.cleaned_data.get("target_roles", []),
                    form=form,
                    saved_draft=False,
                )
                if action == "preview"
                else {"form": form, "update": update},
            )

        if action != "save":
            return HttpResponseBadRequest("Invalid system update form action.")

        # A published release is immutable; re-check under a lock to prevent stale draft edits.
        with transaction.atomic():
            if update:
                get_object_or_404(SystemUpdate.objects.select_for_update(), pk=update.pk, is_published=False)
            saved = form.save(commit=False)
            if not saved.created_by_id:
                saved.created_by = request.user
            saved.save()
            form.save_m2m()

        messages.success(request, "System update draft saved.")
        return redirect("manage_system_updates")

    return render(request, "notifications/update_form.html", {"form": form, "update": update})


@manager_required
def update_preview(request, update_id):
    update = get_object_or_404(SystemUpdate, pk=update_id, is_published=False)
    return render(
        request,
        "notifications/update_preview.html",
        _preview_context(
            update,
            update.target_roles,
            saved_draft=True,
        ),
    )


@manager_required
@require_POST
def update_action(request, update_id):
    with transaction.atomic():
        update = get_object_or_404(SystemUpdate.objects.select_for_update(), pk=update_id)
        action = request.POST.get("action")
        if action == "publish" and not update.is_published:
            update.full_clean()
            update.is_published = True
            update.published_at = timezone.now()
        elif action == "hide_popup" and update.is_published:
            update.show_popup = False
        else:
            return HttpResponseBadRequest("Invalid system update action.")
        update.save()
    messages.success(request, "System update saved.")
    return redirect("manage_system_updates")
