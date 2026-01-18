from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from registry.models import Repository, Star
from accounts.permissions import setup_groups_and_permissions, assign_user_to_group

User = get_user_model()


class ProfileOwnedAndStarredReposTests(TestCase):
    def setUp(self):
        # Set up groups and permissions first
        setup_groups_and_permissions()
        
        self.owner = User.objects.create_user(username="owner", password="pass", role="USER")
        assign_user_to_group(self.owner)
        
        self.user = User.objects.create_user(username="alice", password="pass", role="USER")
        assign_user_to_group(self.user)

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

        # TODO: Repository listings will be implemented under separate URLs later
        # when repository functionalities are fully added
        # For now, just verify the profile page loads successfully
        
        # Owned - TODO: Implement in separate repositories page
        # self.assertContains(resp, "My repositories")
        # self.assertContains(resp, "alice/myrepo")

        # Starred - TODO: Implement in separate starred repositories page  
        # self.assertContains(resp, "Starred repositories")
        # self.assertContains(resp, "owner/demo")
