from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from registry.models import Repository, Star

User = get_user_model()


class ProfileOwnedAndStarredReposTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass", role="USER")
        self.user = User.objects.create_user(username="alice", password="pass", role="USER")

        self.owned_repo = Repository.objects.create(
            owner=self.user,
            name="myrepo",
            description="",
            visibility=Repository.Visibility.PUBLIC,
            is_official=False,
        )

        self.other_repo = Repository.objects.create(
            owner=self.owner,
            name="demo",
            description="",
            visibility=Repository.Visibility.PUBLIC,
            is_official=False,
        )

    def test_profile_requires_login(self):
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 302)

    def test_profile_lists_owned_and_starred(self):
        Star.objects.create(user=self.user, repository=self.other_repo)

        self.client.login(username="alice", password="pass")
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 200)

        # Owned
        self.assertContains(resp, "My repositories")
        self.assertContains(resp, "alice/myrepo")

        # Starred
        self.assertContains(resp, "Starred repositories")
        self.assertContains(resp, "owner/demo")
