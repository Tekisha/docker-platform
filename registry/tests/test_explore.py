"""
Unit tests for public search and explore functionality.
Tests cover: search, badge filtering, relevance scoring, pagination, star_count caching.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from registry.models import Repository, Star
from registry.utils import calculate_relevance_score, search_public_repositories, get_repository_badges

User = get_user_model()


@pytest.fixture
def setup_test_data(db):
    regular_user = User.objects.create_user(
        username='regular',
        password='test123',
        email='regular@test.com',
        role=User.UserRole.USER,
        publisher_status=User.PublisherStatus.NONE
    )
    
    verified_user = User.objects.create_user(
        username='verified',
        password='test123',
        email='verified@test.com',
        role=User.UserRole.USER,
        publisher_status=User.PublisherStatus.VERIFIED_PUBLISHER
    )
    
    sponsored_user = User.objects.create_user(
        username='sponsored',
        password='test123',
        email='sponsored@test.com',
        role=User.UserRole.USER,
        publisher_status=User.PublisherStatus.SPONSORED_OSS
    )
    
    admin_user = User.objects.create_user(
        username='admin',
        password='test123',
        email='admin@test.com',
        role=User.UserRole.ADMIN
    )
    
    # Create repositories with different characteristics
    official_repo = Repository.objects.create(
        owner=admin_user,
        name='nginx',
        description='Official Nginx web server',
        visibility=Repository.Visibility.PUBLIC,
        is_official=True,
        pull_count=100000,
        star_count=50
    )
    
    verified_repo = Repository.objects.create(
        owner=verified_user,
        name='verified-app',
        description='Application from verified publisher',
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
        pull_count=5000,
        star_count=20
    )
    
    sponsored_repo = Repository.objects.create(
        owner=sponsored_user,
        name='sponsored-oss',
        description='Sponsored open source project',
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
        pull_count=2000,
        star_count=15
    )
    
    regular_repo = Repository.objects.create(
        owner=regular_user,
        name='regular-app',
        description='Regular user application',
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
        pull_count=100,
        star_count=5
    )
    
    private_repo = Repository.objects.create(
        owner=regular_user,
        name='private-app',
        description='Private repository',
        visibility=Repository.Visibility.PRIVATE,
        is_official=False,
        pull_count=50,
        star_count=2
    )
    
    # Set different update times for time relevance testing
    old_repo = Repository.objects.create(
        owner=regular_user,
        name='old-app',
        description='Old application',
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
        pull_count=1000,
        star_count=10
    )
    # Use update() to bypass auto_now on updated_at
    Repository.objects.filter(id=old_repo.id).update(
        updated_at=timezone.now() - timedelta(days=180)
    )
    old_repo.refresh_from_db()
    
    return {
        'users': {
            'regular': regular_user,
            'verified': verified_user,
            'sponsored': sponsored_user,
            'admin': admin_user,
        },
        'repos': {
            'official': official_repo,
            'verified': verified_repo,
            'sponsored': sponsored_repo,
            'regular': regular_repo,
            'private': private_repo,
            'old': old_repo,
        }
    }


@pytest.mark.django_db
class TestPublicSearch:
    """Test search_public_repositories function"""
    
    def test_search_returns_only_public_repos(self, setup_test_data):
        """Verify that search excludes private repositories"""
        results = search_public_repositories()
        
        assert results.count() == 5  # 5 public, 1 private
        assert setup_test_data['repos']['private'] not in results
    
    def test_search_by_name(self, setup_test_data):
        """Test text search by repository name"""
        results = search_public_repositories(query='nginx')
        
        assert results.count() == 1
        assert results.first() == setup_test_data['repos']['official']
    
    def test_search_by_description(self, setup_test_data):
        """Test text search by description"""
        results = search_public_repositories(query='verified publisher')
        
        assert results.count() == 1
        assert results.first() == setup_test_data['repos']['verified']
    
    def test_search_by_owner_username(self, setup_test_data):
        """Test search by owner username"""
        results = search_public_repositories(query='sponsored')
        
        assert results.count() == 1
        assert results.first() == setup_test_data['repos']['sponsored']
    
    def test_filter_by_official_badge(self, setup_test_data):
        """Test filtering by official badge"""
        results = search_public_repositories(badge_filters=['OFFICIAL'])
        
        assert results.count() == 1
        assert results.first().is_official is True
    
    def test_filter_by_verified_badge(self, setup_test_data):
        """Test filtering by verified publisher badge"""
        results = search_public_repositories(badge_filters=['VERIFIED'])
        
        assert results.count() == 1
        assert results.first().owner.publisher_status == User.PublisherStatus.VERIFIED_PUBLISHER
    
    def test_filter_by_sponsored_badge(self, setup_test_data):
        """Test filtering by sponsored OSS badge"""
        results = search_public_repositories(badge_filters=['SPONSORED'])
        
        assert results.count() == 1
        assert results.first().owner.publisher_status == User.PublisherStatus.SPONSORED_OSS
    
    def test_filter_by_multiple_badges(self, setup_test_data):
        """Test OR logic for multiple badge filters"""
        results = search_public_repositories(badge_filters=['OFFICIAL', 'VERIFIED'])
        
        assert results.count() == 2  # Official + Verified repos
    
    def test_search_with_query_and_filters(self, setup_test_data):
        """Test combining text search with badge filters"""
        results = search_public_repositories(query='app', badge_filters=['VERIFIED'])
        
        assert results.count() == 1
        assert results.first() == setup_test_data['repos']['verified']



@pytest.mark.django_db
class TestRelevanceScoring:
    """Test calculate_relevance_score function"""
    
    def test_relevance_score_calculated(self, setup_test_data):
        """Verify that relevance scores are calculated for all repos"""
        repos = Repository.objects.filter(visibility=Repository.Visibility.PUBLIC)
        scored_repos = calculate_relevance_score(repos)
        
        for repo in scored_repos:
            assert hasattr(repo, 'relevance_score')
            assert repo.relevance_score > 0
    
    def test_official_repo_has_highest_score(self, setup_test_data):
        """Official repos should have higher scores due to badge boost"""
        repos = Repository.objects.filter(visibility=Repository.Visibility.PUBLIC)
        scored_repos = list(calculate_relevance_score(repos))
        
        # Official repo should be first (highest score)
        assert scored_repos[0] == setup_test_data['repos']['official']
    
    def test_high_pull_count_increases_score(self, setup_test_data):
        """Repos with higher pull_count should have higher scores"""
        official = setup_test_data['repos']['official']
        regular = setup_test_data['repos']['regular']
        
        repos = Repository.objects.filter(id__in=[official.id, regular.id])
        scored = {r.id: r.relevance_score for r in calculate_relevance_score(repos)}
        
        assert scored[official.id] > scored[regular.id]
    
    def test_star_count_affects_score(self, setup_test_data):
        """Repos with more stars should have higher scores"""
        official = setup_test_data['repos']['official']  # 50 stars
        regular = setup_test_data['repos']['regular']    # 5 stars
        
        repos = Repository.objects.filter(id__in=[official.id, regular.id])
        scored = list(calculate_relevance_score(repos))
        
        official_scored = next(r for r in scored if r.id == official.id)
        regular_scored = next(r for r in scored if r.id == regular.id)
        assert official_scored.relevance_score > regular_scored.relevance_score
    
    def test_old_repos_have_lower_time_score(self, setup_test_data):
        """Old repositories should have lower time relevance scores"""
        recent = setup_test_data['repos']['regular']
        old = setup_test_data['repos']['old']
        
        # Verify that old repo is actually older
        assert old.updated_at < recent.updated_at
        
        repos = Repository.objects.filter(id__in=[recent.id, old.id])
        scored = list(calculate_relevance_score(repos))
        
        # Find scored repos
        recent_scored = next(r for r in scored if r.id == recent.id)
        old_scored = next(r for r in scored if r.id == old.id)
        
        # Recent repo should have higher time_score due to fresher updated_at
        # Check that time_score is higher for recent repo
        assert recent_scored.time_score > old_scored.time_score


@pytest.mark.django_db
class TestRepositoryBadges:
    """Test get_repository_badges function"""
    
    def test_official_repo_has_official_badge(self, setup_test_data):
        """Official repositories should have official badge"""
        repo = setup_test_data['repos']['official']
        badges = get_repository_badges(repo)
        
        assert len(badges) == 1
        assert badges[0]['type'] == 'official'
        assert badges[0]['label'] == 'Docker Official Image'
    
    def test_verified_publisher_badge(self, setup_test_data):
        """Verified publisher repos should have verified badge"""
        repo = setup_test_data['repos']['verified']
        badges = get_repository_badges(repo)
        
        assert len(badges) == 1
        assert badges[0]['type'] == 'verified'
        assert badges[0]['label'] == 'Verified Publisher'
    
    def test_sponsored_oss_badge(self, setup_test_data):
        """Sponsored OSS repos should have sponsored badge"""
        repo = setup_test_data['repos']['sponsored']
        badges = get_repository_badges(repo)
        
        assert len(badges) == 1
        assert badges[0]['type'] == 'sponsored'
        assert badges[0]['label'] == 'Sponsored OSS'
    
    def test_regular_repo_has_no_badges(self, setup_test_data):
        """Regular repositories should have no badges"""
        repo = setup_test_data['repos']['regular']
        badges = get_repository_badges(repo)
        
        assert len(badges) == 0


@pytest.mark.django_db
class TestExploreView:
    """Test the explore view endpoint"""
    
    def test_explore_view_accessible(self, setup_test_data):
        """Explore page should be accessible without authentication"""
        client = Client()
        response = client.get(reverse('explore'))
        
        assert response.status_code == 200
        assert 'repositories' in response.context
    
    def test_explore_shows_only_public_repos(self, setup_test_data):
        """Explore view should only show public repositories"""
        client = Client()
        response = client.get(reverse('explore'))
        
        repos = response.context['repositories']
        assert setup_test_data['repos']['private'] not in repos
    
    def test_explore_search_query(self, setup_test_data):
        """Explore view should filter by search query"""
        client = Client()
        response = client.get(reverse('explore'), {'q': 'nginx'})
        
        repos = list(response.context['repositories'])
        assert len(repos) == 1
        assert repos[0] == setup_test_data['repos']['official']
    
    def test_explore_badge_filter(self, setup_test_data):
        """Explore view should filter by badges"""
        client = Client()
        response = client.get(reverse('explore'), {'badges': ['OFFICIAL']})
        
        repos = list(response.context['repositories'])
        assert len(repos) == 1
        assert repos[0].is_official is True
    
    def test_explore_pagination(self, setup_test_data):
        """Explore view should paginate results"""
        # Create 25 repos to test pagination (20 per page)
        user = setup_test_data['users']['regular']
        for i in range(25):
            Repository.objects.create(
                owner=user,
                name=f'test-repo-{i}',
                visibility=Repository.Visibility.PUBLIC,
                is_official=False
            )
        
        client = Client()
        response = client.get(reverse('explore'))
        
        assert 'page_obj' in response.context
        assert response.context['page_obj'].paginator.count >= 25
        assert len(response.context['repositories']) == 20  # First page
    
    def test_explore_repos_sorted_by_relevance(self, setup_test_data):
        """Explore view should sort repos by relevance score"""
        client = Client()
        response = client.get(reverse('explore'))
        
        repos = list(response.context['repositories'])
        
        # Official repo should be first (highest relevance)
        assert repos[0] == setup_test_data['repos']['official']
        
        # Check that scores are descending
        for i in range(len(repos) - 1):
            assert repos[i].relevance_score >= repos[i + 1].relevance_score
