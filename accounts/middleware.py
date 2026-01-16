from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class MustChangePasswordMiddleware(MiddlewareMixin):
    """
    If authenticated user has must_change_password=True,
    block access to everything except allowed paths.
    """

    def process_request(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        if not getattr(user, "must_change_password", False):
            return None

        allowed_names = {
            "password_change",
            "password_change_done",
            "logout",
            "login",
        }

        # Allow admin login page to render, but block admin app pages
        # We'll handle this via route check below.

        current_path = request.path

        # Allow static/media (optional)
        if current_path.startswith("/static/") or current_path.startswith("/media/"):
            return None

        # Allow the explicitly whitelisted named routes
        try:
            allowed_paths = {reverse(name) for name in allowed_names}
        except Exception:
            allowed_paths = set()

        # Also allow /accounts/ prefix routes for password change and login/logout
        if current_path in allowed_paths:
            return None

        # If user tries to access admin or any other page -> redirect to password change
        return redirect("password_change")
