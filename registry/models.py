import uuid

from django.conf import settings
from django.db import models

class Repository(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC"
        PRIVATE = "PRIVATE"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="repositories")
    name = models.CharField(max_length=200, db_index=True)
    description = models.CharField(max_length=500, blank=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    is_official = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pull_count = models.IntegerField(default=0)
    star_count = models.IntegerField(default=0, db_index=True)

    class Meta:
        unique_together = [("owner", "name")]
        indexes = [
            models.Index(fields=['visibility', '-pull_count'], name='repo_vis_pull_idx'),
            models.Index(fields=['visibility', '-updated_at'], name='repo_vis_upd_idx'),
            models.Index(fields=['is_official'], name='repo_official_idx'),
        ]

    def __str__(self):
        return f"{self.owner.username}/{self.name}" if not self.is_official else self.name


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=128)
    digest = models.CharField(max_length=200, blank=True)
    size = models.BigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("repository", "name")]
        indexes = [
            models.Index(fields=['repository', '-created_at'], name='tag_repo_date_idx'),
        ]

    def __str__(self):
        return f"{self.repository}:{self.name}"


class Star(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stars")
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="stars")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['repository'], name='star_repo_idx'),
            models.Index(fields=['user', 'repository'], name='star_user_repo_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "repository"], name="unique_star_per_user_repo")
        ]

    def __str__(self):
        return f"{self.user.username} ★ {self.repository}"
