from django.contrib import admin
from .models import Repository, Tag

@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "visibility", "is_official", "created_at")
    search_fields = ("name", "owner__username")

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "repository", "created_at")
    search_fields = ("name", "repository__name")
