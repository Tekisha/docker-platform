from django.core.exceptions import PermissionDenied

def require_admin_role(user):
    return user.is_authenticated and user.role in ("ADMIN", "SUPERADMIN")

def admin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if not require_admin_role(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped
