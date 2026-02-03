from django.urls import path
from django.contrib.auth import views as auth_views

from . import views_admin, views_profile, views_create_admin, views
from .views import ForcedPasswordChangeView, CustomLoginView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),

    # Forced password change route
    path("password/change/", ForcedPasswordChangeView.as_view(), name="password_change"),
    path("password/change/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),

    # User management and profile
    path("admin/users/", views_admin.admin_user_list, name="admin_user_list"),
    path("admin/users/<uuid:user_id>/publisher-status/", views_admin.set_publisher_status, name="set_publisher_status"),
    path("profile/", views_profile.profile, name="profile"),
    path("profile/starred/", views_profile.starred_repositories, name="starred_repositories"),
    path("admin/create-admin/", views_create_admin.create_admin, name="create_admin"),

    # Redirect repositories to registry app
    path("repositories/", views.redirect_to_repositories, name="repositories"),
    path("analytics/", views.analytics, name="analytics"),
]
