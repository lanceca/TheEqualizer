from .context import reset_current_actor, set_current_actor


class AuditRequestMiddleware:
    """Expose the authenticated request user to audit signal handlers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actor = None
        user = getattr(request, "user", None)

        if (
            user is not None
            and getattr(user, "is_authenticated", False)
        ):
            actor = user

        token = set_current_actor(actor)

        try:
            return self.get_response(request)
        finally:
            reset_current_actor(token)
