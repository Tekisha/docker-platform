from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_POST

from accounts.permissions import (
    repository_management_permission_required,
    permission_required_with_403
)
from .models import Repository
from .forms import (
    RepositoryForm,
    OfficialRepositoryForm,
    RepositoryEditForm,
    RepositorySearchForm
)


@repository_management_permission_required
def repository_list(request):
    """List user's repositories with simple search"""
    user = request.user
    form = RepositorySearchForm(request.GET)

    # Get user's repositories
    repositories = Repository.objects.filter(owner=user).select_related('owner').annotate(
        tag_count=Count('tags'),
        star_count=Count('stars')
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
    """View repository details"""
    repository = get_object_or_404(Repository, id=repo_id)

    # Check permissions - users can view their own repos, admins can view their own + official repos
    can_view = (
        repository.owner == request.user or  # Own repository
        (request.user.has_perm('accounts.can_manage_official_repos') and repository.is_official)  # Admin viewing official repo
    )
    if not can_view:
        messages.error(request, "You don't have permission to view this repository.")
        return redirect('repository_list')

    # Get tags (simple listing, no advanced filtering)
    tags = repository.tags.all().order_by('-created_at')

    # Pagination for tags
    paginator = Paginator(tags, 20)
    page_number = request.GET.get('page')
    tags_page = paginator.get_page(page_number)

    # Check if user has starred this repository
    user_starred = False
    if request.user.is_authenticated and request.user.has_perm('accounts.can_star_repositories'):
        user_starred = repository.stars.filter(user=request.user).exists()

    context = {
        'repository': repository,
        'tags': tags_page,
        'user_starred': user_starred,
        'can_edit': repository.owner == request.user or (request.user.has_perm('accounts.can_manage_official_repos') and repository.is_official),
        'can_star': request.user.has_perm('accounts.can_star_repositories') and repository.owner != request.user,
        'star_count': repository.stars.count(),
    }

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
        tag_count=Count('tags'),
        star_count=Count('stars')
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
