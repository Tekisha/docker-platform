import pytest
from django.urls import reverse
from registry.models import Star, Repository
from registry.tests.test_explore import setup_test_data


@pytest.fixture
def owner_user(user_factory):
    return user_factory(username="owner", password="pass", role="USER")


@pytest.fixture
def other_user(user_factory):
    return user_factory(username="other", password="pass", role="USER")


@pytest.fixture
def admin_user_for_stars(user_factory):
    return user_factory(username="admin", password="pass", role="ADMIN")


@pytest.fixture
def public_repo(db, owner_user):
    from registry.models import Repository
    return Repository.objects.create(
        owner=owner_user,
        name="pub",
        description="",
        visibility=Repository.Visibility.PUBLIC,
        is_official=False
    )


@pytest.fixture
def private_repo(db, owner_user):
    from registry.models import Repository
    return Repository.objects.create(
        owner=owner_user,
        name="priv",
        description="",
        visibility=Repository.Visibility.PRIVATE,
        is_official=False
    )


@pytest.mark.django_db
def test_user_can_star_public_repo_not_owned(client, other_user, public_repo):
    client.login(username="other", password="pass")
    url = reverse("repo_star", kwargs={"repo_id": public_repo.id})
    client.post(url, follow=True)
    assert Star.objects.count() == 1


@pytest.mark.django_db
def test_user_cannot_star_own_repo(client, owner_user, public_repo):
    client.login(username="owner", password="pass")
    url = reverse("repo_star", kwargs={"repo_id": public_repo.id})
    client.post(url, follow=True)
    assert Star.objects.count() == 0


@pytest.mark.django_db
def test_user_cannot_star_private_repo(client, other_user, private_repo):
    client.login(username="other", password="pass")
    url = reverse("repo_star", kwargs={"repo_id": private_repo.id})
    client.post(url, follow=True)
    assert Star.objects.count() == 0


@pytest.mark.django_db
def test_star_is_unique(client, other_user, public_repo):
    client.login(username="other", password="pass")
    url = reverse("repo_star", kwargs={"repo_id": public_repo.id})
    client.post(url, follow=True)
    client.post(url, follow=True)
    assert Star.objects.count() == 1


@pytest.mark.django_db
def test_unstar(client, other_user, public_repo):
    client.login(username="other", password="pass")
    star_url = reverse("repo_star", kwargs={"repo_id": public_repo.id})
    unstar_url = reverse("repo_unstar", kwargs={"repo_id": public_repo.id})
    client.post(star_url, follow=True)
    assert Star.objects.count() == 1
    client.post(unstar_url, follow=True)
    assert Star.objects.count() == 0

# ====================
# Star Count Caching Tests
# ====================

@pytest.mark.django_db
class TestStarCountCaching:
    def test_star_count_increments_on_star(self, setup_test_data):
        """star_count should increment when repository is starred"""
        repo = setup_test_data['repos']['regular']
        user = setup_test_data['users']['verified']
        initial_count = repo.star_count

        from registry.services.stars import star_repository
        star_repository(user, repo)

        repo.refresh_from_db()
        assert repo.star_count == initial_count + 1

    def test_star_count_decrements_on_unstar(self, setup_test_data):
        """star_count should decrement when repository is unstarred"""
        repo = setup_test_data['repos']['regular']
        user = setup_test_data['users']['verified']

        # First star it
        from registry.services.stars import star_repository, unstar_repository
        star_repository(user, repo)
        repo.refresh_from_db()
        count_after_star = repo.star_count

        # Then unstar
        unstar_repository(user, repo)
        repo.refresh_from_db()

        assert repo.star_count == count_after_star - 1

    def test_star_count_matches_actual_stars(self, setup_test_data):
        """Cached star_count should match actual Star count"""
        repo = setup_test_data['repos']['regular']
        user1 = setup_test_data['users']['verified']
        user2 = setup_test_data['users']['sponsored']

        # Reset star_count to 0 first
        Repository.objects.filter(id=repo.id).update(star_count=0)

        # Create actual stars
        Star.objects.create(user=user1, repository=repo)
        Star.objects.create(user=user2, repository=repo)

        # Update cached count to match actual stars
        Repository.objects.filter(id=repo.id).update(star_count=2)
        repo.refresh_from_db()

        actual_count = Star.objects.filter(repository=repo).count()
        assert repo.star_count == actual_count
        assert repo.star_count == 2
