import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .permissions import superadmin_required, assign_user_to_group

User = get_user_model()


def _generate_temp_password() -> str:
    return secrets.token_urlsafe(16)


@superadmin_required
@require_http_methods(["GET", "POST"])
def create_admin(request):
    if request.method == "GET":
        return render(request, "accounts/create_admin.html")

    username = (request.POST.get("username") or "").strip()
    email = (request.POST.get("email") or "").strip()
    temp_password = (request.POST.get("temp_password") or "").strip()

    # basic validation
    if not username:
        messages.error(request, "Username is required.")
        return render(request, "accounts/create_admin.html")

    if email:
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Email is not valid.")
            return render(request, "accounts/create_admin.html")

    if User.objects.filter(username=username).exists():
        messages.error(request, "Username already exists.")
        return render(request, "accounts/create_admin.html")

    if not temp_password:
        temp_password = _generate_temp_password()

    admin_user = User.objects.create_user(
        username=username,
        email=email,
        password=temp_password,
    )

    # Your project roles
    admin_user.role = "ADMIN"
    admin_user.must_change_password = True  # recommended: force change on first login

    # Django admin UI flags
    admin_user.is_staff = True
    admin_user.is_superuser = False

    admin_user.save(update_fields=["role", "must_change_password", "is_staff", "is_superuser"])

    # Assign user to appropriate group
    assign_user_to_group(admin_user)

    messages.success(request, f"Admin '{username}' created. Temporary password: {temp_password}")
    return redirect("admin_user_list")  # reuse your existing admin users page
