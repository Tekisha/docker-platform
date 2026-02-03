"""
Integration tests for explore and star functionality.
Tests complete user journeys from login through actions to verification.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from registry.models import Repository, Star

User = get_user_model()


@pytest.fixture
def test_users(db):
    """Create test users with different roles"""
    regular = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        role=User.UserRole.USER,
        publisher_status=User.PublisherStatus.NONE
    )
    
    verified = User.objects.create_user(
        username='verified_dev',
        email='verified@example.com',
        password='testpass123',
        role=User.UserRole.USER,
        publisher_status=User.PublisherStatus.VERIFIED_PUBLISHER
    )
    
    superadmin = User.objects.create_user(
        username='superadmin',
        email='admin@example.com',
        password='testpass123',
        role=User.UserRole.SUPERADMIN,
        is_superuser=True,
        is_staff=True
    )
    
    return {
        'regular': regular,
        'verified': verified,
        'superadmin': superadmin
    }


@pytest.fixture
def test_repositories(db, test_users):
    """Create test repositories"""
    official = Repository.objects.create(
        owner=test_users['superadmin'],
        name='nginx',
        description='Official nginx image',
        visibility=Repository.Visibility.PUBLIC,
        is_official=True,
        pull_count=10000,
        star_count=0
    )
    
    verified_repo = Repository.objects.create(
        owner=test_users['verified'],
        name='cool-app',
        description='Cool application',
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
        pull_count=500,
        star_count=0
    )
    
    user_repo = Repository.objects.create(
        owner=test_users['regular'],
        name='my-app',
        description='My personal app',
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
        pull_count=50,
        star_count=0
    )
    
    private_repo = Repository.objects.create(
        owner=test_users['regular'],
        name='secret-app',
        description='Private repository',
        visibility=Repository.Visibility.PRIVATE,
        is_official=False,
        pull_count=10,
        star_count=0
    )
    
    return {
        'official': official,
        'verified': verified_repo,
        'user': user_repo,
        'private': private_repo
    }


@pytest.mark.django_db
class TestUnauthenticatedExplore:
    """Test explore functionality for unauthenticated users"""
    
    def test_can_view_explore_page(self, test_repositories):
        """Unauthenticated users can view explore page"""
        client = Client()
        response = client.get(reverse('explore'))
        
        assert response.status_code == 200
        assert 'repositories' in response.context
    
    def test_sees_only_public_repos(self, test_repositories):
        """Unauthenticated users see only public repositories"""
        client = Client()
        response = client.get(reverse('explore'))
        
        repos = list(response.context['repositories'])
        
        # Should see 3 public repos, not private
        assert len(repos) == 3
        assert test_repositories['private'] not in repos
    
    def test_can_search_repositories(self, test_repositories):
        """Unauthenticated users can search repositories"""
        client = Client()
        response = client.get(reverse('explore'), {'q': 'nginx'})
        
        repos = list(response.context['repositories'])
        assert len(repos) == 1
        assert repos[0] == test_repositories['official']
    
    def test_can_filter_by_badges(self, test_repositories):
        """Unauthenticated users can filter by badges"""
        client = Client()
        response = client.get(reverse('explore'), {'badges': ['OFFICIAL']})
        
        repos = list(response.context['repositories'])
        assert len(repos) == 1
        assert repos[0].is_official is True
    
    def test_cannot_star_without_login(self, test_repositories):
        """Unauthenticated users cannot star repositories"""
        client = Client()
        response = client.post(
            reverse('repo_star', args=[test_repositories['official'].id]),
            follow=False
        )
        
        # Should redirect to login or return 302/403
        assert response.status_code in [302, 403]
        
        # No star should be created
        assert Star.objects.count() == 0



@pytest.mark.django_db
class TestAuthenticatedUserExplore:
    """Test complete authenticated user journey"""
    
    def test_login_explore_search_star_flow(self, test_users, test_repositories):
        """Complete flow: login -> explore -> search -> star -> verify"""
        client = Client()
        user = test_users['regular']
        repo = test_repositories['verified']
        
        # Step 1: Login
        login_success = client.login(username='testuser', password='testpass123')
        assert login_success is True
        
        # Step 2: Access explore page
        response = client.get(reverse('explore'))
        assert response.status_code == 200
        
        # Step 3: Search for specific repo
        response = client.get(reverse('explore'), {'q': 'cool-app'})
        repos = list(response.context['repositories'])
        assert len(repos) == 1
        assert repos[0] == repo
        
        # Step 4: Star the repository
        response = client.post(
            reverse('repo_star', args=[repo.id]),
            follow=True
        )
        assert response.status_code == 200
        
        # Step 5: Verify star was created
        assert Star.objects.filter(user=user, repository=repo).exists()
        
        # Step 6: Check star count incremented
        repo.refresh_from_db()
        assert repo.star_count == 1
    
    def test_star_appears_in_starred_page(self, test_users, test_repositories):
        """Starred repos should appear in starred repositories page"""
        client = Client()
        user = test_users['regular']
        repo = test_repositories['official']
        
        # Login and star
        client.login(username='testuser', password='testpass123')
        client.post(reverse('repo_star', args=[repo.id]))
        
        # Check starred repositories page
        response = client.get(reverse('starred_repositories'))
        assert response.status_code == 200
        
        starred_repos = response.context['repositories']
        assert repo in starred_repos
    
    def test_unstar_removes_from_starred_page(self, test_users, test_repositories):
        """Unstarring should remove repo from starred repositories page"""
        client = Client()
        user = test_users['regular']
        repo = test_repositories['official']
        
        # Login, star, then unstar
        client.login(username='testuser', password='testpass123')
        client.post(reverse('repo_star', args=[repo.id]))
        client.post(reverse('repo_unstar', args=[repo.id]))
        
        # Verify star removed
        assert not Star.objects.filter(user=user, repository=repo).exists()
        
        # Check star_count decremented
        repo.refresh_from_db()
        assert repo.star_count == 0
        
        # Check starred page is empty
        response = client.get(reverse('starred_repositories'))
        assert len(response.context['repositories']) == 0
    
    def test_cannot_star_own_repository(self, test_users, test_repositories):
        """Users cannot star their own repositories"""
        client = Client()
        user = test_users['regular']
        own_repo = test_repositories['user']
        
        # Login
        client.login(username='testuser', password='testpass123')
        
        # Try to star own repo
        response = client.post(
            reverse('repo_star', args=[own_repo.id]),
            follow=True
        )
        
        # Star should not be created
        assert not Star.objects.filter(user=user, repository=own_repo).exists()


@pytest.mark.django_db
class TestSuperadminExplore:
    """Test superadmin can star official repos they didn't create"""
    
    def test_superadmin_can_star_official_repos(self, test_users, test_repositories):
        """Superadmin can star official repos created by other admins"""
        client = Client()
        superadmin = test_users['superadmin']
        
        # Create another admin's official repo
        other_admin = User.objects.create_user(
            username='other_admin',
            password='test123',
            role=User.UserRole.ADMIN
        )
        
        official_repo = Repository.objects.create(
            owner=other_admin,
            name='postgres',
            description='Official PostgreSQL',
            visibility=Repository.Visibility.PUBLIC,
            is_official=True,
            pull_count=5000,
            star_count=0
        )
        
        # Login as superadmin
        client.login(username='superadmin', password='testpass123')
        
        # Star the official repo
        response = client.post(
            reverse('repo_star', args=[official_repo.id]),
            follow=True
        )
        
        # Verify star created
        assert Star.objects.filter(user=superadmin, repository=official_repo).exists()
        official_repo.refresh_from_db()
        assert official_repo.star_count == 1
    
    def test_superadmin_cannot_star_own_repos(self, test_users, test_repositories):
        """Superadmin cannot star their own repositories"""
        client = Client()
        superadmin = test_users['superadmin']
        own_official = test_repositories['official']
        
        # Login
        client.login(username='superadmin', password='testpass123')
        
        # Try to star own repo
        response = client.post(
            reverse('repo_star', args=[own_official.id]),
            follow=True
        )
        
        # Should not create star
        assert not Star.objects.filter(user=superadmin, repository=own_official).exists()


@pytest.mark.django_db
class TestRelevanceSortingIntegration:
    """Test that relevance scoring affects explore results"""
    
    def test_explore_sorts_by_relevance(self, test_users, test_repositories):
        """Explore page should sort repos by relevance score"""
        client = Client()
        response = client.get(reverse('explore'))
        
        repos = list(response.context['repositories'])
        
        # Official repo (high pull_count + badge) should be first
        assert repos[0] == test_repositories['official']
        
        # Scores should be descending
        for i in range(len(repos) - 1):
            assert repos[i].relevance_score >= repos[i + 1].relevance_score
    
    def test_starred_repos_score_higher(self, test_users, test_repositories):
        """Repos with stars should have higher relevance scores"""
        client = Client()
        
        # Have users star the verified repo
        for username in ['testuser', 'verified_dev']:
            user = User.objects.get(username=username)
            Star.objects.create(user=user, repository=test_repositories['verified'])
        
        # Update star_count
        test_repositories['verified'].star_count = 2
        test_repositories['verified'].save()
        
        # Get explore results
        response = client.get(reverse('explore'))
        repos = list(response.context['repositories'])
        
        # Find verified repo in results
        verified_in_results = next(r for r in repos if r.id == test_repositories['verified'].id)
        user_repo_in_results = next(r for r in repos if r.id == test_repositories['user'].id)
        
        # Verified repo (with stars) should score higher than user repo (no stars)
        assert verified_in_results.relevance_score > user_repo_in_results.relevance_score

