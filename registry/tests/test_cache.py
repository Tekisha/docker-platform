"""
Redis cache tests for registry app (pytest style)
"""
import pytest
from django.core.cache import cache
from django.test import Client
from django.contrib.auth import get_user_model

from registry.models import Repository, Tag, Star
from registry.cache_keys import CacheKeys
from registry.cache import invalidate_repository_cache, invalidate_explore_cache

User = get_user_model()


# ==================== FIXTURES ====================

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        password='testpass123'
    )


@pytest.fixture
def public_repo(db, user):
    return Repository.objects.create(
        owner=user,
        name='test-repo',
        visibility=Repository.Visibility.PUBLIC
    )


@pytest.fixture
def private_repo(db, user):
    return Repository.objects.create(
        owner=user,
        name='private-repo',
        visibility=Repository.Visibility.PRIVATE
    )


@pytest.fixture
def client():
    return Client()

@pytest.fixture(autouse=True, scope='function')
def clear_cache():
    cache.clear()
    yield
    cache.clear()

# ==================== CACHE KEYS TESTS ====================

class TestCacheKeys:
    """Test CacheKeys class generates correct keys"""

    def test_explore_key_no_params(self):
        key = CacheKeys.explore(query=None, badges=None)
        assert key == "explore:q:None:badges:"

    def test_explore_key_with_query(self):
        key = CacheKeys.explore(query="test", badges=None)
        assert key == "explore:q:test:badges:"

    def test_explore_key_with_badges(self):
        key = CacheKeys.explore(query=None, badges=["official", "verified"])
        assert "official" in key
        assert "verified" in key

    def test_repo_detail_public_key(self):
        key = CacheKeys.repo_detail_public("test-repo-id")
        assert key == "repo_detail_public:test-repo-id"

    def test_repo_tags_key(self):
        key = CacheKeys.repo_tags("test-repo-id")
        assert key == "repo_tags:test-repo-id"

    def test_get_repo_invalidation_keys(self):
        keys = CacheKeys.get_repo_invalidation_keys("test-id")
        assert isinstance(keys, list)
        assert len(keys) > 0
        assert any("repo_detail_public:test-id" in k for k in keys)


# ==================== EXPLORE CACHE TESTS ====================

@pytest.mark.django_db
class TestExploreCache:
    """Test explore view caching via behavior observation"""

    def test_explore_cache_miss_then_hit(self, client, public_repo, capfd):
        """Test explore view caches results by observing cache logs"""
        # First request - should log CACHE MISS
        response1 = client.get('/explore/')
        assert response1.status_code == 200

        # Capture output
        out, err = capfd.readouterr()
        assert "[CACHE MISS] Exploring" in out, "First request should be cache miss"

        # Second request - should log CACHE HIT
        response2 = client.get('/explore/')
        assert response2.status_code == 200

        out, err = capfd.readouterr()
        assert "[CACHE HIT] Exploring" in out, "Second request should be cache hit"

    def test_explore_cache_with_query(self, client, public_repo, capfd):
        """Test explore caches different queries separately"""
        # Request without query
        response1 = client.get('/explore/')
        assert response1.status_code == 200
        out1, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out1

        # Request with query - should be separate cache miss
        response2 = client.get('/explore/?q=test')
        assert response2.status_code == 200
        out2, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out2, "Different query should be cache miss"

        # Repeat no-query request - should hit cache
        response3 = client.get('/explore/')
        assert response3.status_code == 200
        out3, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out3, "Repeated no-query should hit cache"

        # Repeat query request - should hit cache
        response4 = client.get('/explore/?q=test')
        assert response4.status_code == 200
        out4, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out4, "Repeated query should hit cache"

    def test_explore_cache_different_badges(self, client, public_repo, capfd):
        """Test explore caches different badge filters separately"""
        # Request without badges
        response1 = client.get('/explore/')
        assert response1.status_code == 200
        out1, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out1

        # Request with badge filter - different cache
        response2 = client.get('/explore/?badges=official')
        assert response2.status_code == 200
        out2, _ = capfd.readouterr()
        assert response2.status_code == 200

        # Repeat first request - should hit cache
        response3 = client.get('/explore/')
        assert response3.status_code == 200
        out3, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out3


# ==================== PUBLIC REPO DETAIL CACHE TESTS ====================

@pytest.mark.django_db
class TestPublicRepositoryDetailCache:
    """Test public repository detail caching via behavior observation"""

    def test_public_repo_detail_cached(self, client, public_repo, capfd):
        """Test public repository detail is cached"""
        url = f'/registry/public/{public_repo.id}/'

        # First request - cache miss
        response1 = client.get(url)
        assert response1.status_code == 200
        out1, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out1, "First request should be cache miss"

        # Second request - cache hit
        response2 = client.get(url)
        assert response2.status_code == 200
        out2, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out2, "Second request should be cache hit"

    def test_private_repo_not_accessible_as_public(self, client, private_repo):
        """Test private repository cannot be accessed via public URL"""
        url = f'/registry/public/{private_repo.id}/'
        response = client.get(url)

        # Should redirect (not accessible)
        assert response.status_code == 302, "Private repo should redirect"

    def test_public_repo_cache_hit_rate(self, client, public_repo, capfd):
        """Test multiple requests to same repo use cache"""
        url = f'/registry/public/{public_repo.id}/'

        # First request - cache miss
        response1 = client.get(url)
        assert response1.status_code == 200
        out1, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out1

        # Multiple subsequent requests - should all hit cache
        for i in range(2, 6):
            response = client.get(url)
            assert response.status_code == 200
            out, _ = capfd.readouterr()
            assert "[CACHE HIT]" in out, f"Request {i} should hit cache"


# ==================== SIGNAL INVALIDATION TESTS ====================

@pytest.mark.django_db
class TestSignalInvalidation:
    """Test automatic cache invalidation via signals"""

    def test_repository_edit_invalidates_cache(self, public_repo):
        """Test editing repository invalidates its cache"""
        cache_key = CacheKeys.repo_detail_public(public_repo.id)

        # VERIFY: Cache is empty initially
        assert cache.get(cache_key) is None, "Cache should be empty initially"

        # Populate cache manually
        cache.set(cache_key, {'test': 'data'}, 600)

        # VERIFY: Cache now exists
        assert cache.get(cache_key) is not None, "Cache should exist after manual set"

        # Edit repository (triggers signal)
        public_repo.description = "Updated description"
        public_repo.save()

        # VERIFY: Cache is invalidated
        cached_data = cache.get(cache_key)
        assert cached_data is None, "Cache should be invalidated after repo edit"

    def test_repository_delete_invalidates_cache(self, public_repo):
        """Test deleting repository invalidates cache"""
        cache_key = CacheKeys.repo_detail_public(public_repo.id)

        # VERIFY: Cache is empty initially
        assert cache.get(cache_key) is None, "Cache should be empty initially"

        # Populate cache
        cache.set(cache_key, {'test': 'data'}, 600)

        # VERIFY: Cache exists
        assert cache.get(cache_key) is not None, "Cache should exist after manual set"

        # Delete repository (triggers signal)
        public_repo.delete()

        # VERIFY: Cache is invalidated
        assert cache.get(cache_key) is None, "Cache should be invalidated after repo delete"

    def test_tag_push_invalidates_repo_cache(self, public_repo):
        """Test pushing tag invalidates repository cache"""
        cache_key = CacheKeys.repo_detail_public(public_repo.id)

        # VERIFY: Cache is empty initially
        assert cache.get(cache_key) is None, "Cache should be empty initially"

        # Populate cache
        cache.set(cache_key, {'test': 'data'}, 600)

        # VERIFY: Cache exists
        assert cache.get(cache_key) is not None, "Cache should exist after manual set"

        # Create tag (simulates Docker push, triggers signal)
        Tag.objects.create(
            repository=public_repo,
            name='latest',
            digest='sha256:abc123'
        )

        # VERIFY: Cache is invalidated
        assert cache.get(cache_key) is None, "Cache should be invalidated after tag push"

    def test_star_invalidates_caches(self, user, public_repo):
        """Test starring repository invalidates related caches"""
        repo_key = CacheKeys.repo_detail_public(public_repo.id)
        explore_key = CacheKeys.explore(query=None, badges=None)

        # VERIFY: Caches are empty initially
        assert cache.get(repo_key) is None, "Repo cache should be empty initially"
        assert cache.get(explore_key) is None, "Explore cache should be empty initially"

        # Populate caches
        cache.set(repo_key, {'test': 'repo'}, 600)
        cache.set(explore_key, {'test': 'explore'}, 600)

        # VERIFY: Caches now exist
        assert cache.get(repo_key) is not None, "Repo cache should exist after set"
        assert cache.get(explore_key) is not None, "Explore cache should exist after set"

        # Create star (triggers signal)
        Star.objects.create(user=user, repository=public_repo)

        # VERIFY: Both caches are invalidated
        assert cache.get(repo_key) is None, "Repo cache should be invalidated after star"
        assert cache.get(explore_key) is None, "Explore cache should be invalidated (star count affects sorting)"

    def test_unstar_invalidates_caches(self, user, public_repo):
        """Test unstarring repository invalidates caches"""
        repo_key = CacheKeys.repo_detail_public(public_repo.id)

        # Create star first
        star = Star.objects.create(user=user, repository=public_repo)

        # VERIFY: Cache is empty initially
        assert cache.get(repo_key) is None, "Cache should be empty initially"

        # Populate cache
        cache.set(repo_key, {'test': 'data'}, 600)

        # VERIFY: Cache exists
        assert cache.get(repo_key) is not None, "Cache should exist after set"

        # Delete star (triggers signal)
        star.delete()

        # VERIFY: Cache is invalidated
        assert cache.get(repo_key) is None, "Cache should be invalidated after unstar"


# ==================== CACHE INVALIDATION FUNCTION TESTS ====================

@pytest.mark.django_db
class TestCacheInvalidationFunctions:
    """Test cache invalidation utility functions"""

    def test_invalidate_repository_cache(self, public_repo):
        """Test invalidate_repository_cache deletes correct keys"""
        keys = CacheKeys.get_repo_invalidation_keys(public_repo.id)

        # VERIFY: All keys are empty initially
        for key in keys:
            assert cache.get(key) is None, f"Key {key} should be empty initially"

        # Populate all repo-related cache keys
        for key in keys:
            cache.set(key, 'data', 600)

        # VERIFY: All keys are now cached
        for key in keys:
            assert cache.get(key) is not None, f"Key {key} should be cached after set"

        # Invalidate all repo caches
        invalidate_repository_cache(public_repo.id)

        # VERIFY: All keys are deleted
        for key in keys:
            assert cache.get(key) is None, f"Key {key} should be deleted after invalidation"

    def test_invalidate_explore_cache(self):
        """Test invalidate_explore_cache deletes explore keys"""
        key1 = CacheKeys.explore(query=None, badges=None)
        key2 = CacheKeys.explore(query="test", badges=[])

        # VERIFY: Both keys are empty initially
        assert cache.get(key1) is None, "Explore key 1 should be empty initially"
        assert cache.get(key2) is None, "Explore key 2 should be empty initially"

        # Populate explore cache entries
        cache.set(key1, 'data1', 600)
        cache.set(key2, 'data2', 600)

        # VERIFY: Both keys are now cached
        assert cache.get(key1) is not None, "Explore key 1 should be cached after set"
        assert cache.get(key2) is not None, "Explore key 2 should be cached after set"

        # Invalidate all explore caches
        invalidate_explore_cache()

        # VERIFY: Both keys are deleted
        assert cache.get(key1) is None, "Explore key 1 should be deleted after invalidation"
        assert cache.get(key2) is None, "Explore key 2 should be deleted after invalidation"


# ==================== INTEGRATION TESTS ====================

@pytest.mark.django_db
class TestCacheIntegration:
    """Integration tests - full cache lifecycle via behavior observation"""

    def test_full_cache_lifecycle(self, client, user, public_repo, capfd):
        """Test complete cache lifecycle: populate → hit → invalidate → repopulate"""
        # 1. First request - cache miss
        response1 = client.get('/explore/')
        assert response1.status_code == 200
        out1, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out1, "First request should be cache miss"

        # 2. Second request - cache hit
        response2 = client.get('/explore/')
        assert response2.status_code == 200
        out2, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out2, "Second request should be cache hit"

        # 3. Edit repo - invalidates cache via signal
        public_repo.description = "Updated"
        public_repo.save()
        out3, _ = capfd.readouterr()
        assert "[SIGNAL] Repository changed" in out3, "Signal should fire"
        assert "[CACHE] Invalidated" in out3, "Cache should be invalidated"

        # 4. Third request - cache miss again (repopulate)
        response3 = client.get('/explore/')
        assert response3.status_code == 200
        out4, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out4, "After invalidation should be cache miss"

        # 5. Fourth request - cache hit again
        response4 = client.get('/explore/')
        assert response4.status_code == 200
        out5, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out5, "After repopulation should be cache hit"

    def test_public_repo_detail_lifecycle(self, client, public_repo, capfd):
        """Test public repo detail cache lifecycle"""
        url = f'/registry/public/{public_repo.id}/'

        # 1. Request 1 - cache miss
        response1 = client.get(url)
        assert response1.status_code == 200
        out1, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out1

        # 2. Request 2 - cache hit
        response2 = client.get(url)
        assert response2.status_code == 200
        out2, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out2

        # 3. Edit repo - invalidate
        public_repo.description = "New description"
        public_repo.save()
        out3, _ = capfd.readouterr()
        assert "[SIGNAL] Repository changed" in out3

        # 4. Request 3 - cache miss (repopulate)
        response3 = client.get(url)
        assert response3.status_code == 200
        out4, _ = capfd.readouterr()
        assert "[CACHE MISS]" in out4

        # 5. Request 4 - cache hit
        response4 = client.get(url)
        assert response4.status_code == 200
        out5, _ = capfd.readouterr()
        assert "[CACHE HIT]" in out5
