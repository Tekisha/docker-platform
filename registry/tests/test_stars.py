import pytest
from django.urls import reverse
from registry.models import Star



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
def test_admin_cannot_star(client, admin_user_for_stars, public_repo):
    client.login(username="admin", password="pass")
    url = reverse("repo_star", kwargs={"repo_id": public_repo.id})
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
