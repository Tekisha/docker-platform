import math
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q


def calculate_relevance_score(repositories_queryset):
    now = timezone.now()
    ninety_days_ago = now - timedelta(days=90)
    
    repositories = repositories_queryset.annotate(
        star_count=Count('stars', distinct=True)
    )

    repos_list = []
    
    for repo in repositories:
        # 1. Pull and star count score (logarithmic)
        pull_score = math.log10(repo.pull_count + 1) * 10
        star_score = math.log10(repo.star_count + 1) * 12

        
        # 2. Badge boost
        badge_score = 0
        if repo.is_official:
            badge_score = 40
        elif hasattr(repo.owner, 'publisher_status'):
            if repo.owner.publisher_status == 'VERIFIED_PUBLISHER':
                badge_score = 30
            elif repo.owner.publisher_status == 'SPONSORED_OSS':
                badge_score = 20
        
        # 3. Time relevance boost
        days = (now - repo.updated_at).days
        time_score = 15 * math.exp(-days / 60)
        
        relevance_score = pull_score + star_score + badge_score + time_score
        
        # Store score with repo
        repo.relevance_score = round(relevance_score, 2)
        repo.star_count_display = repo.star_count
        repos_list.append(repo)

    repos_list.sort(key=lambda r: r.relevance_score, reverse=True)
    
    return repos_list


def search_public_repositories(query=None, badge_filters=None):
    from .models import Repository
    
    repositories = Repository.objects.filter(
        visibility=Repository.Visibility.PUBLIC
    ).select_related('owner').prefetch_related('stars')

    if query:
        repositories = repositories.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(owner__username__icontains=query)
        )
    
    # Apply badge filters
    if badge_filters:
        badge_q = Q()
        if 'OFFICIAL' in badge_filters:
            badge_q |= Q(is_official=True)
        if 'VERIFIED' in badge_filters:
            badge_q |= Q(owner__publisher_status='VERIFIED_PUBLISHER')
        if 'SPONSORED' in badge_filters:
            badge_q |= Q(owner__publisher_status='SPONSORED_OSS')
        if badge_q:
            repositories = repositories.filter(badge_q)
    
    return repositories


def get_repository_badges(repository):
    badges = []

    if repository.is_official:
        badges.append({
            'type': 'official',
            'label': 'Docker Official Image',
            'class': 'badge bg-primary'
        })

    if hasattr(repository.owner, 'publisher_status'):
        if repository.owner.publisher_status == 'VERIFIED_PUBLISHER':
            badges.append({
                'type': 'verified',
                'label': 'Verified Publisher',
                'class': 'badge bg-success'
            })
        elif repository.owner.publisher_status == 'SPONSORED_OSS':
            badges.append({
                'type': 'sponsored',
                'label': 'Sponsored OSS',
                'class': 'badge bg-info'
            })

    return badges
