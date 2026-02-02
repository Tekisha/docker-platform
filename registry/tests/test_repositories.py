import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client

from registry.models import Repository
from accounts.permissions import setup_groups_and_permissions

User = get_user_model()


@pytest.fixture
def setup_permissions(db):
    """Set up groups and permissions"""
    setup_groups_and_permissions()


@pytest.fixture
def users(db, setup_permissions):
    """Create test users with different roles"""
    regular_user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        role='USER'
    )

    admin_user = User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
        role='ADMIN'
    )

    superadmin_user = User.objects.create_user(
        username='superadmin',
        email='superadmin@example.com',
        password='superadminpass123',
        role='SUPERADMIN'
    )

    return {
        'regular': regular_user,
        'admin': admin_user,
        'superadmin': superadmin_user
    }


@pytest.fixture
def repositories(db, users):
    """Create test repositories"""
    user_repo = Repository.objects.create(
        name='test-repo',
        description='A test repository',
        visibility='PUBLIC',
        owner=users['regular']
    )

    private_repo = Repository.objects.create(
        name='private-repo',
        description='A private repository',
        visibility='PRIVATE',
        owner=users['regular']
    )

    official_repo = Repository.objects.create(
        name='official-repo',
        description='An official repository',
        visibility='PUBLIC',
        is_official=True,
        owner=users['admin']
    )

    return {
        'user_repo': user_repo,
        'private_repo': private_repo,
        'official_repo': official_repo
    }


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.mark.django_db
class TestRepositoryList:
    """Test repository list view"""

    def test_unauthenticated_access_denied(self, client):
        """Test that unauthenticated users cannot access repository list"""
        response = client.get(reverse('repository_list'))
        assert response.status_code == 302  # Redirect to login

    def test_user_sees_only_own_repositories(self, client, users, repositories):
        """Test that regular users see only their own repositories"""
        client.login(username='testuser', password='testpass123')
        response = client.get(reverse('repository_list'))

        assert response.status_code == 200
        assert 'test-repo' in response.content.decode()
        assert 'private-repo' in response.content.decode()
        assert 'official-repo' not in response.content.decode()

    def test_search_functionality(self, client, users, repositories):
        """Test repository search functionality"""
        client.login(username='testuser', password='testpass123')

        # Search for specific repository
        response = client.get(reverse('repository_list'), {'search': 'test'})
        assert response.status_code == 200
        assert 'test-repo' in response.content.decode()
        assert 'private-repo' not in response.content.decode()


@pytest.mark.django_db
class TestRepositoryCreate:
    """Test repository creation"""

    def test_create_regular_repository(self, client, users):
        """Test creating a regular repository"""
        client.login(username='testuser', password='testpass123')

        data = {
            'name': 'new-repo',
            'description': 'A new test repository',
            'visibility': 'PUBLIC'
        }

        response = client.post(reverse('repository_create'), data)
        assert response.status_code == 302  # Redirect after success

        # Check that repository was created
        repo = Repository.objects.get(name='new-repo', owner=users['regular'])
        assert repo.description == 'A new test repository'
        assert repo.visibility == 'PUBLIC'
        assert repo.is_official is False

    def test_create_official_repository_as_admin(self, client, users):
        """Test that admin can create official repositories"""
        client.login(username='admin', password='adminpass123')

        data = {
            'name': 'new-official-repo',
            'description': 'A new official repository',
            'visibility': 'PUBLIC'
        }

        response = client.post(reverse('repository_create') + '?official=true', data)
        assert response.status_code == 302

        # Check that official repository was created
        repo = Repository.objects.get(name='new-official-repo')
        assert repo.is_official is True

    def test_regular_user_cannot_create_official_repository(self, client, users):
        """Test that regular users cannot create official repositories"""
        client.login(username='testuser', password='testpass123')

        data = {
            'name': 'unofficial-repo',
            'description': 'Should not be official',
            'visibility': 'PUBLIC'
        }

        # Try to create official repository as regular user
        response = client.post(reverse('repository_create') + '?official=true', data)
        assert response.status_code == 302

        # Check that repository is not official
        repo = Repository.objects.get(name='unofficial-repo', owner=users['regular'])
        assert repo.is_official is False

    def test_duplicate_name_validation(self, client, users, repositories):
        """Test that duplicate repository names are not allowed for same user"""
        client.login(username='testuser', password='testpass123')

        data = {
            'name': 'test-repo',  # This name already exists for this user
            'description': 'Duplicate name',
            'visibility': 'PUBLIC'
        }

        response = client.post(reverse('repository_create'), data)
        assert response.status_code == 200  # Form should not be valid
        assert 'already have a repository' in response.content.decode()


@pytest.mark.django_db
class TestRepositoryDetail:
    """Test repository detail view"""

    def test_view_own_repository(self, client, users, repositories):
        """Test viewing own repository"""
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('repository_detail', args=[repositories['user_repo'].id]))
        assert response.status_code == 200
        assert 'test-repo' in response.content.decode()

    def test_view_others_private_repository_denied(self, client, users, repositories):
        """Test that users cannot view others' private repositories"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123',
            role='USER'
        )
        client.login(username='otheruser', password='otherpass123')

        response = client.get(reverse('repository_detail', args=[repositories['private_repo'].id]))
        assert response.status_code == 302  # Should redirect

    def test_admin_can_view_official_repository(self, client, users, repositories):
        """Test that admins can view official repositories"""
        client.login(username='admin', password='adminpass123')

        response = client.get(reverse('repository_detail', args=[repositories['official_repo'].id]))
        assert response.status_code == 200
        assert 'official-repo' in response.content.decode()

    def test_admin_cannot_view_other_users_repository(self, client, users, repositories):
        """Test that admins cannot view other users' personal repositories"""
        client.login(username='admin', password='adminpass123')

        response = client.get(reverse('repository_detail', args=[repositories['private_repo'].id]))
        assert response.status_code == 302  # Should redirect


@pytest.mark.django_db
class TestRepositoryEdit:
    """Test repository editing"""

    def test_edit_own_repository(self, client, users, repositories):
        """Test editing own repository"""
        client.login(username='testuser', password='testpass123')

        data = {
            'description': 'Updated description',
            'visibility': 'PRIVATE'
        }

        response = client.post(reverse('repository_edit', args=[repositories['user_repo'].id]), data)
        assert response.status_code == 302

        # Check that repository was updated
        repositories['user_repo'].refresh_from_db()
        assert repositories['user_repo'].description == 'Updated description'
        assert repositories['user_repo'].visibility == 'PRIVATE'

    def test_cannot_edit_others_repository(self, client, users, repositories):
        """Test that users cannot edit others' repositories"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123',
            role='USER'
        )
        client.login(username='otheruser', password='otherpass123')

        response = client.get(reverse('repository_edit', args=[repositories['user_repo'].id]))
        assert response.status_code == 302  # Should redirect


@pytest.mark.django_db
class TestRepositoryDelete:
    """Test repository deletion"""

    def test_delete_own_repository(self, client, users, repositories):
        """Test deleting own repository"""
        client.login(username='testuser', password='testpass123')

        repo_id = repositories['user_repo'].id
        response = client.post(reverse('repository_delete', args=[repo_id]))
        assert response.status_code == 302

        # Check that repository was deleted
        assert not Repository.objects.filter(id=repo_id).exists()

    def test_cannot_delete_others_repository(self, client, users, repositories):
        """Test that users cannot delete others' repositories"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123',
            role='USER'
        )
        client.login(username='otheruser', password='otherpass123')

        repo_id = repositories['user_repo'].id
        response = client.post(reverse('repository_delete', args=[repo_id]))
        assert response.status_code == 302  # Should redirect

        # Repository should still exist
        assert Repository.objects.filter(id=repo_id).exists()


@pytest.mark.django_db
class TestAdminRepositoryView:
    """Test admin repository management views"""

    def test_admin_official_repositories(self, client, users, repositories):
        """Test that admins can view official repositories"""
        client.login(username='admin', password='adminpass123')

        response = client.get(reverse('admin_repository_list'))
        assert response.status_code == 200

        # Should see official repositories but not other users' personal repositories
        content = response.content.decode()
        assert 'official-repo' in content  # Can see official repo

    def test_regular_user_cannot_access_admin_view(self, client, users):
        """Test that regular users cannot access admin repository view"""
        client.login(username='testuser', password='testpass123')

        response = client.get(reverse('admin_repository_list'))
        assert response.status_code == 403  # Permission denied


@pytest.mark.django_db
class TestRepositoryModel:
    """Test repository model functionality"""

    def test_repository_string_representation(self):
        """Test repository __str__ method"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        repo = Repository.objects.create(
            name='test-repo',
            owner=user
        )
        assert str(repo) == 'testuser/test-repo'

        # Test official repository
        official_repo = Repository.objects.create(
            name='official-repo',
            owner=user,
            is_official=True
        )
        assert str(official_repo) == 'official-repo'

    def test_repository_unique_constraint(self):
        """Test that repository names are unique per user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        Repository.objects.create(name='test-repo', owner=user)

        # Creating another repository with same name for same user should fail
        with pytest.raises(Exception):
            Repository.objects.create(name='test-repo', owner=user)
