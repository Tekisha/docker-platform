from accounts.permissions import get_user_permissions_context


def user_permissions(request):
    """
    Add user permissions to template context.
    """
    if hasattr(request, 'user'):
        return get_user_permissions_context(request.user)
    return {}