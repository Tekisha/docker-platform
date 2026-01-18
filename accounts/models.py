import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    class UserRole(models.TextChoices):
        SUPERADMIN = "SUPERADMIN"
        ADMIN = "ADMIN"
        USER = "USER"

    class PublisherStatus(models.TextChoices):
        NONE = "NONE"
        VERIFIED_PUBLISHER = "VERIFIED_PUBLISHER"
        SPONSORED_OSS = "SPONSORED_OSS"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authorization
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

    # Explore / badge logic
    publisher_status = models.CharField(
        max_length=30,
        choices=PublisherStatus.choices,
        default=PublisherStatus.NONE,
    )

    # Setup requirement
    must_change_password = models.BooleanField(default=False)

    # -------- helpers --------
    def is_admin(self) -> bool:
        return self.role in {self.UserRole.ADMIN, self.UserRole.SUPERADMIN}

    def is_superadmin(self) -> bool:
        return self.role == self.UserRole.SUPERADMIN

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_role = None
        
        if not is_new:
            try:
                old_instance = User.objects.get(pk=self.pk)
                old_role = old_instance.role
            except User.DoesNotExist:
                # Handle edge case where pk exists but object doesn't
                is_new = True
        
        super().save(*args, **kwargs)
        
        # Assign to groups if role changed or new user
        if is_new or old_role != self.role:
            self._assign_to_group()
    
    def _assign_to_group(self):
        """Assign user to appropriate group based on role"""
        try:
            from accounts.permissions import assign_user_to_group
            assign_user_to_group(self)
        except Exception:
            # Groups might not be set up yet, ignore silently
            pass
