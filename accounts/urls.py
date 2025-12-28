from django.urls import path
from django.contrib.auth import views as auth_views

from . import views_admin
from .views import ForcedPasswordChangeView

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Forced password change route
    path("password/change/", ForcedPasswordChangeView.as_view(), name="password_change"),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),

    path("admin/users/", views_admin.admin_user_list, name="admin_user_list"),
    path("admin/users/<uuid:user_id>/publisher-status/", views_admin.set_publisher_status, name="set_publisher_status"),

]
