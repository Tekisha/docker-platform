from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from registry.models import Repository
from registry.services.stars import star_repository, unstar_repository


@require_POST
def star(request, repo_id):
    repo = get_object_or_404(Repository, id=repo_id)
    try:
        star_repository(request.user, repo)
    except PermissionDenied:
        pass  # Silently ignore permission errors
    return redirect(request.META.get("HTTP_REFERER", "/"))


@require_POST
def unstar(request, repo_id):
    repo = get_object_or_404(Repository, id=repo_id)
    try:
        unstar_repository(request.user, repo)
    except PermissionDenied:
        pass  # Silently ignore permission errors
    return redirect(request.META.get("HTTP_REFERER", "/"))
