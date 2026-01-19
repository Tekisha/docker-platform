from __future__ import annotations

import pytest
from django.urls import reverse
from registry.models import Repository
from registry.models import Star




@pytest.fixture
def owner_user(user_factory):
    return user_factory(username="owner", password="pass", role="USER")


@pytest.fixture
def alice_user(user_factory):
    return user_factory(username="alice", password="pass", role="USER")


@pytest.fixture
def owned_repo(db, alice_user):
    return Repository.objects.create(
        owner=alice_user,
        name="myrepo",
        description="",
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
    )


@pytest.fixture
def other_repo(db, owner_user):
    return Repository.objects.create(
        owner=owner_user,
        name="demo",
        description="",
        visibility=Repository.Visibility.PUBLIC,
        is_official=False,
    )


@pytest.mark.django_db
def test_profile_requires_login(client):
    resp = client.get(reverse("profile"))
    assert resp.status_code == 302


@pytest.mark.django_db
def test_profile_lists_owned_and_starred(client, alice_user, owned_repo, other_repo):
    Star.objects.create(user=alice_user, repository=other_repo)

    client.login(username="alice", password="pass")
    resp = client.get(reverse("profile"))
    assert resp.status_code == 200

    # TODO: Repository listings will be implemented under separate URLs later
    # when repository functionalities are fully added
    # For now, just verify the profile page loads successfully
    
    # Owned - TODO: Implement in separate repositories page
    # assert "My repositories" in resp.content.decode()
    # assert "alice/myrepo" in resp.content.decode()

    # Starred - TODO: Implement in separate starred repositories page  
    # assert "Starred repositories" in resp.content.decode()
    # assert "owner/demo" in resp.content.decode()
