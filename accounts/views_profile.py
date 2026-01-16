from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from registry.models import Repository, Star


@login_required
def profile(request):
    user = request.user

    owned_repos = (
        Repository.objects
        .filter(owner=user)
        .annotate(star_count=Count("stars"))
        .order_by("-created_at")
    )

    starred_repos = (
        Repository.objects
        .filter(stars__user=user)
        .annotate(star_count=Count("stars"))
        .select_related("owner")
        .order_by("-stars__created_at")
        .distinct()
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "user_obj": user,
            "owned_repos": owned_repos,
            "starred_repos": starred_repos,
        },
    )
