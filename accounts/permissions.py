from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps


def setup_groups_and_permissions():
    """
    Set up Django groups and permissions for the application.
    Should be called during system initialization.
    """
    # Get or create groups
    admin_group, _ = Group.objects.get_or_create(name='Administrators')
    superadmin_group, _ = Group.objects.get_or_create(name='Super Administrators')
    user_group, _ = Group.objects.get_or_create(name='Users')
    
    # Create custom permissions
    from accounts.models import User
    content_type = ContentType.objects.get_for_model(User)
    
    # Define custom permissions
    permissions_to_create = [
        ('can_manage_users', 'Can manage users'),
        ('can_view_analytics', 'Can view analytics'),
        ('can_create_admins', 'Can create administrators'),
        ('can_manage_official_repos', 'Can manage official repositories'),
        ('can_manage_repositories', 'Can manage repositories'),
        ('can_star_repositories', 'Can star repositories'),
    ]
    
    # Create permissions if they don't exist
    for codename, name in permissions_to_create:
        Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )
    
    # Assign permissions to groups
    # Super Admin permissions (all)
    superadmin_permissions = [
        'can_manage_users',
        'can_view_analytics', 
        'can_create_admins',
        'can_manage_official_repos',
        'can_manage_repositories',
        'can_star_repositories',
    ]
    
    # Admin permissions (subset)
    admin_permissions = [
        'can_manage_users',
        'can_view_analytics',
        'can_manage_official_repos',
        'can_manage_repositories',
        'can_star_repositories',
    ]
    
    # User permissions (basic)
    user_permissions = [
        'can_manage_repositories',
        'can_star_repositories',
    ]
    
    # Clear existing permissions and reassign
    superadmin_group.permissions.clear()
    admin_group.permissions.clear()
    user_group.permissions.clear()
    
    # Assign permissions to Super Admin group
    for perm_codename in superadmin_permissions:
        perm = Permission.objects.get(codename=perm_codename, content_type=content_type)
        superadmin_group.permissions.add(perm)
    
    # Assign permissions to Admin group
    for perm_codename in admin_permissions:
        perm = Permission.objects.get(codename=perm_codename, content_type=content_type)
        admin_group.permissions.add(perm)
    
    # Assign permissions to User group
    for perm_codename in user_permissions:
        perm = Permission.objects.get(codename=perm_codename, content_type=content_type)
        user_group.permissions.add(perm)


def assign_user_to_group(user):
    """
    Assign user to appropriate group based on their role.
    """
    # Remove user from all groups first
    user.groups.clear()
    
    # Assign to appropriate group based on role
    if user.role == 'SUPERADMIN':
        group = Group.objects.get(name='Super Administrators')
        user.groups.add(group)
    elif user.role == 'ADMIN':
        group = Group.objects.get(name='Administrators')
        user.groups.add(group)
    else:  # USER
        group = Group.objects.get(name='Users')
        user.groups.add(group)


def check_setup_required(view_func):
    """
    Decorator to check if system setup is required.
    If superadmin exists and needs password change, redirect accordingly.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        from accounts.models import User
        
        # Check if any superadmin exists
        superadmin = User.objects.filter(role='SUPERADMIN').first()
        
        if superadmin and superadmin.must_change_password:
            # If user is not the superadmin, deny access
            if not request.user.is_authenticated or request.user != superadmin:
                from django.contrib import messages
                messages.error(request, 'System setup is in progress. Please wait.')
                return redirect('login')
            
            # If this is the superadmin but not trying to change password, redirect
            if request.resolver_match.url_name not in ['password_change', 'password_change_done', 'logout']:
                from django.contrib import messages
                messages.warning(request, 'You must change your password before using the system.')
                return redirect('password_change')
        
        return view_func(request, *args, **kwargs)
    return _wrapped


def permission_required_with_403(perm):
    """
    Permission required decorator that raises 403 instead of redirecting to login.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                raise PermissionDenied("You don't have permission to access this resource.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def user_has_permission(user, permission_codename):
    """
    Check if user has a specific permission.
    """
    return user.is_authenticated and user.has_perm(f'accounts.{permission_codename}')


# Specific permission decorators
def admin_required(view_func):
    """
    Require admin or superadmin permissions.
    """
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not (request.user.has_perm('accounts.can_manage_users') or 
                request.user.has_perm('accounts.can_view_analytics')):
            raise PermissionDenied("Administrator privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def superadmin_required(view_func):
    """
    Require superadmin permissions.
    """
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.has_perm('accounts.can_create_admins'):
            raise PermissionDenied("Super Administrator privileges required.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def analytics_permission_required(view_func):
    """
    Require analytics viewing permission.
    """
    return permission_required_with_403('accounts.can_view_analytics')(view_func)


def user_management_permission_required(view_func):
    """
    Require user management permission.
    """
    return permission_required_with_403('accounts.can_manage_users')(view_func)


def repository_management_permission_required(view_func):
    """
    Require repository management permission.
    """
    return permission_required_with_403('accounts.can_manage_repositories')(view_func)


# Template context helpers
def get_user_permissions_context(user):
    """
    Get user permissions for use in templates.
    """
    if not user.is_authenticated:
        return {}
    
    return {
        'can_manage_users': user.has_perm('accounts.can_manage_users'),
        'can_view_analytics': user.has_perm('accounts.can_view_analytics'),
        'can_create_admins': user.has_perm('accounts.can_create_admins'),
        'can_manage_official_repos': user.has_perm('accounts.can_manage_official_repos'),
        'can_manage_repositories': user.has_perm('accounts.can_manage_repositories'),
        'can_star_repositories': user.has_perm('accounts.can_star_repositories'),
        'is_admin': user.has_perm('accounts.can_manage_users') or user.has_perm('accounts.can_view_analytics'),
        'is_superadmin': user.has_perm('accounts.can_create_admins'),
    }