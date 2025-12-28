from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "publisher_status", "is_active")

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("SCM Roles & Badges", {
            "fields": ("role", "publisher_status", "must_change_password"),
        }),
    )
