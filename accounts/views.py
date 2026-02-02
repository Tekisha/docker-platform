from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import LoginForm, UserRegistrationForm
from .models import User
from .permissions import (
    analytics_permission_required,
    assign_user_to_group,
    repository_management_permission_required,
)


class ForcedPasswordChangeView(PasswordChangeView):
    """
    Same as Django PasswordChangeView, but after successful change:
    - clears must_change_password
    - sets last_password_change_at (if present)
    """

    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        user: User = self.request.user
        if getattr(user, 'must_change_password', False):
            user.must_change_password = False
            if hasattr(user, 'last_password_change_at'):
                user.last_password_change_at = timezone.now()
            user.save(
                update_fields=[
                    'must_change_password',
                    *(
                        ['last_password_change_at']
                        if hasattr(user, 'last_password_change_at')
                        else []
                    ),
                ]
            )
        return response


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group
            assign_user_to_group(user)
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def home(request):
    """Home page view - accessible to all users"""
    return render(request, 'home.html')


def explore(request):
    """Explore public repositories - accessible to all users"""
    return render(request, 'todo.html', {'feature_name': 'Explore Repositories'})


@repository_management_permission_required
def redirect_to_repositories(request):
    """Redirect to registry repository list"""
    return redirect('repository_list')


@analytics_permission_required
def analytics(request):
    """Analytics view - for administrators only"""
    return render(request, 'todo.html', {'feature_name': 'Analytics Dashboard'})


class CustomLoginView(LoginView):
    """Custom login view with Bootstrap styled form"""

    form_class = LoginForm
    template_name = 'registration/login.html'
