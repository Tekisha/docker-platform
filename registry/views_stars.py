from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from registry.models import Repository
from registry.services.stars import star_repository, unstar_repository


@require_POST
def star(request, repo_id):
    repo = get_object_or_404(Repository, id=repo_id)
    try:
        created = star_repository(request.user, repo)
        if created:
            messages.success(request, "Repository starred.")
        else:
            messages.info(request, "Repository already starred.")
    except PermissionDenied as e:
        messages.error(request, str(e))
    return redirect(request.META.get("HTTP_REFERER", "/"))


@require_POST
def unstar(request, repo_id):
    repo = get_object_or_404(Repository, id=repo_id)
    try:
        deleted = unstar_repository(request.user, repo)
        if deleted:
            messages.success(request, "Repository unstarred.")
        else:
            messages.info(request, "Repository was not starred.")
    except PermissionDenied as e:
        messages.error(request, str(e))
    return redirect(request.META.get("HTTP_REFERER", "/"))
