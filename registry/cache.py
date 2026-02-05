"""
Redis caching utilities for registry app
"""
from django.core.cache import cache
from django_redis import get_redis_connection
from .cache_keys import CacheKeys


def invalidate_repository_cache(repo_id):
    keys_to_delete = CacheKeys.get_repo_invalidation_keys(repo_id)
    cache.delete_many(keys_to_delete)

    invalidate_explore_cache()

    print(f"[CACHE] Invalidated repository cache: {repo_id}")


def invalidate_user_cache(user_id):
    keys_to_delete = CacheKeys.get_user_invalidation_keys(user_id)
    cache.delete_many(keys_to_delete)
    print(f"[CACHE] Invalidated user cache: {user_id}")


def invalidate_explore_cache():
    try:
        conn = get_redis_connection("default")
        pattern = CacheKeys.get_explore_invalidation_pattern()

        cursor = 0
        deleted_count = 0
        while True:
            cursor, keys = conn.scan(cursor, match=pattern, count=100)
            if keys:
                conn.delete(*keys)
                deleted_count += len(keys)
            if cursor == 0:
                break

        print(f"[CACHE] Invalidated {deleted_count} explore cache entries")
    except Exception as e:
        print(f"[CACHE ERROR] Failed to invalidate explore cache: {e}")
