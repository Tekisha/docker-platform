from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render

from registry.models import Repository, Star


@login_required
def profile(request):
    user = request.user

    owned_repos = (
        Repository.objects
        .filter(owner=user)
        .order_by("-created_at")
    )

    starred_count = (
        Repository.objects
        .filter(stars__user=user)
        .count()
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "user_obj": user,
            "owned_repos": owned_repos,
            "starred_count": starred_count,
        },
    )


@login_required
def starred_repositories(request):
    user = request.user
    
    # Get search query
    query = request.GET.get('q', '').strip()
    
    # Base queryset
    starred_repos = (
        Repository.objects
        .filter(stars__user=user)
        .select_related("owner")
        .order_by("-stars__created_at")
        .distinct()
    )
    
    # Apply search filter
    if query:
        from django.db.models import Q
        starred_repos = starred_repos.filter(
            Q(name__icontains=query) |
            Q(owner__username__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(starred_repos, 20)  # 20 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(
        request,
        "accounts/starred_repositories.html",
        {
            "page_obj": page_obj,
            "repositories": page_obj.object_list,
            "query": query,
        },
    )
