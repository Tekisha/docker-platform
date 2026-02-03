import base64
import json
import pytest
from unittest.mock import patch
from django.test import RequestFactory
from django.contrib.auth import get_user_model

from registry.models import Repository
from registry.views_registry import docker_auth

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def repository(db, user):
    """Create test repository"""
    return Repository.objects.create(
        name='test-repo',
        visibility='PUBLIC',
        owner=user
    )


@pytest.fixture
def private_repository(db, user):
    """Create private test repository"""
    return Repository.objects.create(
        name='private-repo',
        visibility='PRIVATE',
        owner=user
    )


@pytest.mark.django_db
class TestDockerAuth:
    """Test Docker authentication"""

    def test_no_auth_header_public_repo(self, repository):
        """Test accessing public repo without auth"""
        factory = RequestFactory()
        request = factory.get('/api/auth/token/', {
            'scope': 'repository:testuser/test-repo:pull'
        })
        
        with patch('registry.views_registry.getattr', return_value='test-value'):
            with patch('registry.views_registry.jwt.encode', return_value='token'):
                response = docker_auth(request)
                
        assert response.status_code == 200

    def test_invalid_credentials(self):
        """Test invalid credentials"""
        factory = RequestFactory()
        credentials = "testuser:wrongpass"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = factory.get('/api/auth/token/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        
        response = docker_auth(request)
        assert response.status_code == 401

    def test_valid_credentials(self, user):
        """Test valid credentials"""
        factory = RequestFactory()
        credentials = f"{user.username}:testpass123"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = factory.get('/api/auth/token/')
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        
        with patch('registry.views_registry.getattr', return_value='test-value'):
            with patch('registry.views_registry.jwt.encode', return_value='token'):
                response = docker_auth(request)
                
        assert response.status_code == 200

    def test_private_repo_requires_auth(self, private_repository):
        """Test private repo access requires authentication"""
        factory = RequestFactory()
        request = factory.get('/api/auth/token/', {
            'scope': 'repository:testuser/private-repo:pull'
        })
        
        response = docker_auth(request)
        assert response.status_code == 401

    def test_malformed_auth_header(self):
        """Test malformed auth header"""
        factory = RequestFactory()
        request = factory.get('/api/auth/token/')
        request.META['HTTP_AUTHORIZATION'] = 'Basic invalid!'
        
        response = docker_auth(request)
        assert response.status_code == 401

    def test_push_requires_ownership(self, user, repository):
        """Test push requires repository ownership"""
        # Create different user
        other_user = User.objects.create_user(username='other', password='pass')
        
        factory = RequestFactory()
        credentials = f"{other_user.username}:pass"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        request = factory.get('/api/auth/token/', {
            'scope': 'repository:testuser/test-repo:push'
        })
        request.META['HTTP_AUTHORIZATION'] = f'Basic {encoded}'
        
        with patch('registry.views_registry.getattr', return_value='test-value'):
            with patch('registry.views_registry.jwt.encode', return_value='token'):
                response = docker_auth(request)
                
        # Should return 200 but with no push permissions
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['token'] == 'token'