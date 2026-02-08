from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages


class MustChangePasswordMiddleware(MiddlewareMixin):
    """
    1. System setup enforcement (superadmin creation and first login)
    2. Password change requirements for any user with must_change_password=True
    3. Blocking access during system initialization
    """

    def process_request(self, request):
        # Skip for certain paths that should always be accessible
        allowed_paths = ['/static/', '/media/']
        if any(request.path.startswith(path) for path in allowed_paths):
            return None

        # Import here to avoid circular imports
        from accounts.models import User

        # Check if system needs initial setup
        superadmin = User.objects.filter(role='SUPERADMIN').first()

        if not superadmin:
            # No superadmin exists, system needs setup
            self._handle_missing_superadmin(request)
            return None

        # If superadmin exists but needs password change, enforce system-wide setup
        if superadmin.must_change_password:
            return self._handle_system_setup(request, superadmin)

        # System is set up, handle individual user password change requirements
        return self._handle_user_password_change(request)

    def _handle_missing_superadmin(self, request):
        """Handle case where no superadmin exists in the system"""
        # Only allow access to login page and admin (for setup via Django admin if needed)
        allowed_paths = [reverse('login')] if self._safe_reverse('login') else ['/accounts/login/']
        allowed_paths.extend(['/admin/'])

        if request.path not in allowed_paths:
            try:
                messages.error(request, 'System setup required. Please run: python manage.py setup_system')
            except:
                # Handle case where messages framework isn't available (e.g., in tests)
                pass
            return redirect('login') if self._safe_reverse('login') else redirect('/accounts/login/')

    def _handle_system_setup(self, request, superadmin):
        """Handle system setup phase when superadmin needs password change"""
        user = getattr(request, "user", None)

        # Define allowed URLs during setup
        allowed_names = {
            "password_change",
            "password_change_done",
            "logout",
            "login",
        }

        # Get allowed paths, handling cases where URLs might not be available
        allowed_paths = []
        for name in allowed_names:
            path = self._safe_reverse(name)
            if path:
                allowed_paths.append(path)

        # Allow Django admin login (but not other admin pages)
        if request.path == '/admin/login/':
            allowed_paths.append('/admin/login/')

        current_path = request.path

        if not user or not user.is_authenticated:
            # Not authenticated - only allow login and admin login
            if current_path not in [self._safe_reverse('login'), '/admin/login/']:
                return redirect('login') if self._safe_reverse('login') else redirect('/accounts/login/')
            return None

        if user != superadmin:
            # Authenticated but not the superadmin - deny access during setup
            try:
                messages.error(request, 'System setup is in progress. Please wait for the administrator to complete initial setup.')
            except:
                pass
            return redirect('logout') if self._safe_reverse('logout') else redirect('/accounts/logout/')

        # This is the superadmin - check if they're trying to change password
        if current_path not in allowed_paths:
            try:
                messages.warning(request, 'You must change your password before the system can be used.')
            except:
                pass
            return redirect('password_change') if self._safe_reverse('password_change') else redirect('/accounts/password/change/')

        return None

    def _handle_user_password_change(self, request):
        """Handle individual user password change requirements after system is set up"""
        user = getattr(request, "user", None)

        # Only process authenticated users
        if not user or not user.is_authenticated:
            return None

        # Check if this user needs to change password
        if not getattr(user, "must_change_password", False):
            return None

        # User needs to change password - define allowed URLs
        allowed_names = {
            "password_change",
            "password_change_done",
            "logout",
            "login",
        }

        current_path = request.path

        # Allow static/media files
        if current_path.startswith("/static/") or current_path.startswith("/media/"):
            return None

        # Get allowed paths
        allowed_paths = []
        for name in allowed_names:
            path = self._safe_reverse(name)
            if path:
                allowed_paths.append(path)

        # If user is trying to access a non-allowed page, redirect to password change
        if current_path not in allowed_paths:
            try:
                messages.warning(request, 'You must change your password before accessing the system.')
            except:
                pass
            return redirect("password_change") if self._safe_reverse('password_change') else redirect('/accounts/password/change/')

        return None

    def _safe_reverse(self, url_name):
        """Safely reverse URL name, returning None if not found"""
        try:
            return reverse(url_name)
        except:
            return None
