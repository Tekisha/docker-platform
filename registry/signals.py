from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Repository, Tag, Star
from .cache import invalidate_repository_cache, invalidate_user_cache, invalidate_explore_cache


@receiver([post_save, post_delete], sender=Repository)
def invalidate_repo_cache_on_change(sender, instance, **kwargs):
    invalidate_repository_cache(instance.id)
    invalidate_user_cache(instance.owner.id)
    print(f"[SIGNAL] Repository changed: {instance.name}")


@receiver([post_save, post_delete], sender=Tag)
def invalidate_tag_cache_on_change(sender, instance, **kwargs):
    invalidate_repository_cache(instance.repository.id)
    print(f"[SIGNAL] Tag changed for repository: {instance.repository.name}")


@receiver([post_save, post_delete], sender=Star)
def invalidate_star_cache_on_change(sender, instance, **kwargs):
    invalidate_user_cache(instance.user.id)
    invalidate_repository_cache(instance.repository.id)
    invalidate_explore_cache()
    print(f"[SIGNAL] Star changed: {instance.user.username} ★ {instance.repository.name}")
