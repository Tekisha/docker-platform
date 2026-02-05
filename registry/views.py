from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.conf import settings
from .cache_keys import CacheKeys


from accounts.permissions import (
    repository_management_permission_required,
    permission_required_with_403
)
from .models import Repository
from .forms import (
    RepositoryForm,
    OfficialRepositoryForm,
    RepositoryEditForm,
    RepositorySearchForm, PublicSearchForm
)
from .utils import search_public_repositories, get_repository_badges, calculate_relevance_score


@repository_management_permission_required
def repository_list(request):
    """List user's repositories with simple search"""
    user = request.user
    form = RepositorySearchForm(request.GET)

    # Get user's repositories
    repositories = Repository.objects.filter(owner=user).select_related('owner').annotate(
        tag_count=Count('tags')
    )

    # Apply simple search
    if form.is_valid():
        search_query = form.cleaned_data.get('search')

        if search_query:
            repositories = repositories.filter(name__icontains=search_query)

        repositories = repositories.order_by('-updated_at')
    else:
        repositories = repositories.order_by('-updated_at')

    # Pagination
    paginator = Paginator(repositories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'repositories': page_obj,
        'form': form,
        'total_repos': repositories.count(),
        'can_create_official': request.user.has_perm('accounts.can_manage_official_repos'),
    }

    return render(request, 'registry/repository_list.html', context)


@repository_management_permission_required
def repository_create(request):
    """Create a new repository"""
    user = request.user
    can_create_official = user.has_perm('accounts.can_manage_official_repos')
    is_creating_official = request.GET.get('official') == 'true' and can_create_official

    FormClass = OfficialRepositoryForm if is_creating_official else RepositoryForm

    if request.method == 'POST':
        form = FormClass(request.POST, user=user)
        if form.is_valid():
            try:
                repository = form.save(commit=False)
                repository.owner = user
                repository.is_official = is_creating_official
                repository.save()

                messages.success(request, f'Repository "{repository.name}" created successfully!')
                return redirect('repository_detail', repo_id=repository.id)
            except Exception as e:
                form.add_error('name', 'A repository with this name already exists.')
    else:
        form = FormClass(user=user)

    context = {
        'form': form,
        'is_creating_official': is_creating_official,
        'can_create_official': can_create_official,
    }

    return render(request, 'registry/repository_create.html', context)


@repository_management_permission_required
def repository_detail(request, repo_id):
    repository = get_object_or_404(Repository, id=repo_id)

    # Check permissions - users can view their own repos, admins can view their own + official repos
    can_view = (
        repository.owner == request.user or  # Own repository
        (request.user.has_perm('accounts.can_manage_official_repos') and repository.is_official)  # Admin viewing official repo
    )
    if not can_view:
        messages.error(request, "You don't have permission to view this repository.")
        return redirect('repository_list')

    context = _get_repository_detail_context(repository, request)
    return render(request, 'registry/repository_detail.html', context)


def public_repository_detail(request, repo_id):
    repository = get_object_or_404(Repository, id=repo_id)

    # Only allow viewing PUBLIC repositories
    if repository.visibility != Repository.Visibility.PUBLIC:
        messages.error(request, "This repository is private.")
        return redirect('explore')

    cache_key = CacheKeys.repo_detail_public(repo_id)
    context = cache.get(cache_key)


    if context is None:
        user_info = request.user.username if request.user.is_authenticated else "anonymous"
        print(f"[CACHE MISS] Public repository detail: {repo_id} for {user_info}")

        context = _get_repository_detail_context(repository, request)
        context['is_public_view'] = True  # Flag to indicate this is public view

        cache.set(cache_key, context, settings.CACHE_TIMEOUT_REPO_DETAIL)
    else:
        user_info = request.user.username if request.user.is_authenticated else "anonymous"
        print(f"[CACHE HIT] Public repository detail: {repo_id} for {user_info}")

    return render(request, 'registry/repository_detail.html', context)


@repository_management_permission_required
def repository_edit(request, repo_id):
    """Edit repository settings"""
    repository = get_object_or_404(Repository, id=repo_id)

    # Check permissions - users can edit their own repos, admins can edit their own + official repos
    can_edit = (
        repository.owner == request.user or  # Own repository
        (request.user.has_perm('accounts.can_manage_official_repos') and repository.is_official)  # Admin editing official repo
    )
    if not can_edit:
        messages.error(request, "You don't have permission to edit this repository.")
        return redirect('repository_list')

    if request.method == 'POST':
        form = RepositoryEditForm(request.POST, instance=repository)
        if form.is_valid():
            form.save()

            messages.success(request, f'Repository "{repository.name}" updated successfully!')
            return redirect('repository_detail', repo_id=repository.id)
    else:
        form = RepositoryEditForm(instance=repository)

    context = {
        'form': form,
        'repository': repository,
    }

    return render(request, 'registry/repository_edit.html', context)


@repository_management_permission_required
@require_POST
def repository_delete(request, repo_id):
    """Delete a repository"""
    repository = get_object_or_404(Repository, id=repo_id)

    # Check permissions - users can delete their own repos, admins can delete their own + official repos
    can_delete = (
        repository.owner == request.user or  # Own repository
        (request.user.has_perm('accounts.can_manage_official_repos') and repository.is_official)  # Admin deleting official repo
    )
    if not can_delete:
        messages.error(request, "You don't have permission to delete this repository.")
        return redirect('repository_list')

    repository_name = repository.name
    repository.delete()
    messages.success(request, f'Repository "{repository_name}" deleted successfully!')
    return redirect('repository_list')


# Admin-only views for managing all repositories
@permission_required_with_403('accounts.can_manage_official_repos')
def admin_repository_list(request):
    """Admin view to list official repositories """
    form = RepositorySearchForm(request.GET)

    # Get repositories that admin can manage (official repos)
    repositories = Repository.objects.filter(
        Q(is_official=True)
    ).select_related('owner').annotate(
        tag_count=Count('tags')
    )

    # Apply simple search
    if form.is_valid():
        search_query = form.cleaned_data.get('search')

        if search_query:
            repositories = repositories.filter(
                Q(name__icontains=search_query) |
                Q(owner__username__icontains=search_query)
            )

        repositories = repositories.order_by('-updated_at')
    else:
        repositories = repositories.order_by('-updated_at')

    # Pagination
    paginator = Paginator(repositories, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'repositories': page_obj,
        'form': form,
        'total_repos': repositories.count(),
        'is_admin_view': True,
    }

    return render(request, 'registry/admin_repository_list.html', context)


def explore(request):
    form = PublicSearchForm(request.GET or None)

    query = None
    badge_filters = []

    if form.is_valid():
        query = form.cleaned_data.get('q', '').strip()
        badge_filters = form.cleaned_data.get('badges', [])

    cache_key = CacheKeys.explore(query, badge_filters)
    repositories_with_scores = cache.get(cache_key)

    if repositories_with_scores is None:
        print(f"[CACHE MISS] Exploring: query='{query}', badges={badge_filters}")
        repositories = search_public_repositories(query=query, badge_filters=badge_filters)

        repositories_with_scores = calculate_relevance_score(repositories)

        for repo in repositories_with_scores:
            repo.badges = get_repository_badges(repo)

        cache.set(cache_key, repositories_with_scores, settings.CACHE_TIMEOUT_EXPLORE)
    else:
        print(f"[CACHE HIT] Exploring: query='{query}', badges={badge_filters}")

    paginator = Paginator(repositories_with_scores, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'repositories': page_obj,
        'page_obj': page_obj,
        'query': query,
        'badge_filters': badge_filters,
        'total_results': len(repositories_with_scores),
    }

    return render(request, 'explore.html', context)


# Utility functions
def get_repository_stats(user):
    """Get repository statistics for a user"""
    repositories = Repository.objects.filter(owner=user)
    return {
        'total': repositories.count(),
        'public': repositories.filter(visibility='PUBLIC').count(),
        'private': repositories.filter(visibility='PRIVATE').count(),
        'official': repositories.filter(is_official=True).count(),
    }


def _get_repository_detail_context(repository, request):
    tags = repository.tags.all().order_by('-created_at')

    paginator = Paginator(tags, 20)
    page_number = request.GET.get('page')
    tags_page = paginator.get_page(page_number)

    user_starred = False
    if request.user.is_authenticated and request.user.has_perm('accounts.can_star_repositories'):
        user_starred = repository.stars.filter(user=request.user).exists()

    is_owner = request.user.is_authenticated and repository.owner == request.user
    is_admin = request.user.is_authenticated and request.user.has_perm('accounts.can_manage_official_repos')
    can_edit = is_owner or (is_admin and repository.is_official)
    
    can_star = (
        request.user.is_authenticated and 
        request.user.has_perm('accounts.can_star_repositories') and 
        repository.owner != request.user
    )

    return {
        'repository': repository,
        'tags': tags_page,
        'user_starred': user_starred,
        'can_edit': can_edit,
        'can_star': can_star,
        'star_count': repository.star_count,
        'is_owner': is_owner,
    }
