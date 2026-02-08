import json
import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model

from registry.models import Repository, Tag
from registry.views_registry import registry_webhook

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
        name='test-app',
        visibility='PUBLIC',
        owner=user
    )


@pytest.fixture
def official_repository(db, user):
    """Create official repository"""
    return Repository.objects.create(
        name='ubuntu',
        visibility='PUBLIC',
        is_official=True,
        owner=user
    )


@pytest.mark.django_db
class TestWebhook:
    """Test registry webhook functionality"""

    def test_webhook_requires_post(self):
        """Test webhook only accepts POST"""
        factory = RequestFactory()

        request = factory.get('/api/webhooks/registry/')
        response = registry_webhook(request)
        assert response.status_code == 405

    def test_webhook_empty_events(self):
        """Test webhook with empty events"""
        factory = RequestFactory()
        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps({'events': []}),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200

    def test_webhook_invalid_json(self):
        """Test webhook with invalid JSON"""
        factory = RequestFactory()
        request = factory.post('/api/webhooks/registry/',
                              data='invalid json',
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 400

    def test_process_push_event(self, repository):
        """Test processing push event for user repository"""
        factory = RequestFactory()
        push_event = {
            "events": [
                {
                    "id": "test-event-123",
                    "action": "push",
                    "target": {
                        "digest": "sha256:abc123",
                        "size": 1234,
                        "repository": "testuser/test-app",
                        "tag": "latest"
                    }
                }
            ]
        }

        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps(push_event),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200

        # Check tag was created
        tag = Tag.objects.get(repository=repository, name='latest')
        assert tag.digest == "sha256:abc123"
        assert tag.size == 1234

    def test_process_official_repo_push(self, official_repository):
        """Test push to official repository"""
        factory = RequestFactory()
        push_event = {
            "events": [
                {
                    "action": "push",
                    "target": {
                        "digest": "sha256:ubuntu123",
                        "size": 5678,
                        "repository": "ubuntu",
                        "tag": "22.04"
                    }
                }
            ]
        }

        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps(push_event),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200

        # Check tag was created
        tag = Tag.objects.get(repository=official_repository, name='22.04')
        assert tag.digest == "sha256:ubuntu123"

    def test_update_existing_tag(self, repository):
        """Test updating existing tag"""
        # Create initial tag
        Tag.objects.create(
            repository=repository,
            name='latest',
            digest='sha256:old123',
            size=999
        )

        factory = RequestFactory()
        push_event = {
            "events": [
                {
                    "action": "push",
                    "target": {
                        "digest": "sha256:new456",
                        "size": 2000,
                        "repository": "testuser/test-app",
                        "tag": "latest"
                    }
                }
            ]
        }

        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps(push_event),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200

        # Check tag was updated
        tag = Tag.objects.get(repository=repository, name='latest')
        assert tag.digest == "sha256:new456"
        assert tag.size == 2000

    def test_pull_event_increments_pull_count(self, repository):
        """Test that pull events increment repository pull_count"""
        initial_count = repository.pull_count
        
        factory = RequestFactory()
        pull_event = {
            "events": [
                {
                    "action": "pull",
                    "target": {
                        "digest": "sha256:existing123",
                        "size": 1234,
                        "repository": "testuser/test-app",
                        "tag": "latest"
                    }
                }
            ]
        }

        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps(pull_event),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200
        
        # Check pull_count was incremented
        repository.refresh_from_db()
        assert repository.pull_count == initial_count + 1

    def test_pull_official_repo_increments_count(self, official_repository):
        """Test pull event for official repository"""
        initial_count = official_repository.pull_count
        
        factory = RequestFactory()
        pull_event = {
            "events": [
                {
                    "action": "pull",
                    "target": {
                        "digest": "sha256:ubuntu123",
                        "size": 5678,
                        "repository": "ubuntu",
                        "tag": "22.04"
                    }
                }
            ]
        }

        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps(pull_event),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200
        
        # Check pull_count was incremented
        official_repository.refresh_from_db()
        assert official_repository.pull_count == initial_count + 1

    def test_multiple_pulls_increment_correctly(self, repository):
        """Test that multiple pull events increment pull_count correctly"""
        initial_count = repository.pull_count
        
        factory = RequestFactory()
        
        # Send 3 pull events
        for _ in range(3):
            pull_event = {
                "events": [
                    {
                        "action": "pull",
                        "target": {
                            "digest": "sha256:existing123",
                            "size": 1234,
                            "repository": "testuser/test-app",
                            "tag": "latest"
                        }
                    }
                ]
            }
            
            request = factory.post('/api/webhooks/registry/',
                                  data=json.dumps(pull_event),
                                  content_type='application/json')
            
            response = registry_webhook(request)
            assert response.status_code == 200
        
        # Check pull_count incremented by 3
        repository.refresh_from_db()
        assert repository.pull_count == initial_count + 3


    def test_push_unknown_repository(self):
        """Test push to unknown repository"""
        factory = RequestFactory()
        push_event = {
            "events": [
                {
                    "action": "push",
                    "target": {
                        "digest": "sha256:unknown123",
                        "size": 1000,
                        "repository": "unknown/repo",
                        "tag": "latest"
                    }
                }
            ]
        }

        request = factory.post('/api/webhooks/registry/',
                              data=json.dumps(push_event),
                              content_type='application/json')

        response = registry_webhook(request)
        assert response.status_code == 200  # Should handle gracefully
