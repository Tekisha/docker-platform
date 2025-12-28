from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction

from registry.models import Repository, Star


def can_star(user, repo: Repository) -> None:
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required.")

    # Only ordinary users star (admins could be allowed too, but keep it strict)
    if getattr(user, "role", None) != "USER":
        raise PermissionDenied("Only ordinary users can star repositories.")

    if repo.visibility != Repository.Visibility.PUBLIC:
        raise PermissionDenied("You can star only public repositories.")

    if repo.owner_id == user.id:
        raise PermissionDenied("You cannot star your own repository.")


@transaction.atomic
def star_repository(user, repo: Repository) -> bool:
    """
    Returns True if created, False if already existed.
    """
    can_star(user, repo)
    try:
        Star.objects.create(user=user, repository=repo)
        return True
    except IntegrityError:
        # unique constraint hit (already starred)
        return False


@transaction.atomic
def unstar_repository(user, repo: Repository) -> int:
    """
    Returns number of deleted rows (0 or 1).
    """
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required.")

    return Star.objects.filter(user=user, repository=repo).delete()[0]
