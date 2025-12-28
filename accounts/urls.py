from django.urls import path
from django.contrib.auth import views as auth_views
from .views import ForcedPasswordChangeView

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Forced password change route
    path("password/change/", ForcedPasswordChangeView.as_view(), name="password_change"),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
]
