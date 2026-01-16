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
