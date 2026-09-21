"""Shared audience and receipt queries; never use clearable notifications."""
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from accounts.models import User
from .models import SystemUpdate, SystemUpdateReceipt


def visible_updates(user):
    if not user.is_authenticated or not user.is_active or user.role not in User.Role.values:
        return SystemUpdate.objects.none()
    # Indexed JSON lookups support PostgreSQL and local SQLite without fetching
    # the full release history into Python on every workspace request.
    candidates = SystemUpdate.objects.filter(is_published=True, published_at__lte=timezone.now())
    audience = Q(target_roles=[])
    for index in range(len(User.Role.values)):
        audience |= Q(**{f"target_roles__{index}": user.role})
    receipts = SystemUpdateReceipt.objects.filter(update_id=OuterRef("pk"), user=user)
    return candidates.filter(audience).annotate(
        seen=Exists(receipts.filter(seen_at__isnull=False)),
        acknowledged=Exists(receipts.filter(acknowledged_at__isnull=False)),
    )


def pending_updates(user):
    return visible_updates(user).filter(acknowledged=False).filter(
        Q(require_acknowledgement=True) | Q(seen=False)
    )
