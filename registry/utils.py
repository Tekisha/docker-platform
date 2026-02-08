from django.utils import timezone
from django.db.models import (
    Count, Q, F, FloatField, Case, When, Value, 
    ExpressionWrapper, Func
)


# Custom PostgreSQL functions for database-level calculations
class Log10(Func):
    function = 'LOG'
    template = '%(function)s(10, %(expressions)s)'
    output_field = FloatField()


class Exp(Func):
    function = 'EXP'
    output_field = FloatField()


class Extract(Func):
    function = 'EXTRACT'
    template = "%(function)s(EPOCH FROM %(expressions)s)"
    output_field = FloatField()


def calculate_relevance_score(repositories_queryset):
    now = timezone.now()
    
    return repositories_queryset.annotate(
        pull_score=ExpressionWrapper(
            Log10(F('pull_count') + 1) * 8,
            output_field=FloatField()
        ),
        
        star_score=ExpressionWrapper(
            Log10(F('star_count') + 1) * 12,
            output_field=FloatField()
        ),
        
        badge_score=Case(
            When(is_official=True, then=Value(40.0)),
            When(owner__publisher_status='VERIFIED_PUBLISHER', then=Value(25.0)),
            When(owner__publisher_status='SPONSORED_OSS', then=Value(15.0)),
            default=Value(0.0),
            output_field=FloatField()
        ),
        
        days_since_update=ExpressionWrapper(
            Extract(Value(now) - F('updated_at')) / 86400.0,
            output_field=FloatField()
        ),
        time_score=ExpressionWrapper(
            15 * Exp(-F('days_since_update') / 60),
            output_field=FloatField()
        ),
        
        relevance_score=ExpressionWrapper(
            F('pull_score') + F('star_score') + F('badge_score') + F('time_score'),
            output_field=FloatField()
        ),
        
        # Keep star count for display
        star_count_display=F('star_count')
    ).order_by('-relevance_score')


def search_public_repositories(query=None, badge_filters=None):
    from .models import Repository
    
    repositories = Repository.objects.filter(
        visibility=Repository.Visibility.PUBLIC
    ).select_related('owner')

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
