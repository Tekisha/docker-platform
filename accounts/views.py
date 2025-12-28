from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.utils import timezone

from .models import User


class ForcedPasswordChangeView(PasswordChangeView):
    """
    Same as Django PasswordChangeView, but after successful change:
    - clears must_change_password
    - sets last_password_change_at (if present)
    """
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        user: User = self.request.user
        if getattr(user, "must_change_password", False):
            user.must_change_password = False
            if hasattr(user, "last_password_change_at"):
                user.last_password_change_at = timezone.now()
            user.save(update_fields=[
                "must_change_password",
                * (["last_password_change_at"] if hasattr(user, "last_password_change_at") else [])
            ])
        return response
