from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from registry.models import Repository, Star


User = get_user_model()


class StarRulesTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass", role="USER")
        self.other = User.objects.create_user(username="other", password="pass", role="USER")
        self.admin = User.objects.create_user(username="admin", password="pass", role="ADMIN")

        self.public_repo = Repository.objects.create(
            owner=self.owner, name="pub", description="", visibility=Repository.Visibility.PUBLIC, is_official=False
        )
        self.private_repo = Repository.objects.create(
            owner=self.owner, name="priv", description="", visibility=Repository.Visibility.PRIVATE, is_official=False
        )

    def test_user_can_star_public_repo_not_owned(self):
        self.client.login(username="other", password="pass")
        url = reverse("repo_star", kwargs={"repo_id": self.public_repo.id})
        self.client.post(url, follow=True)
        self.assertEqual(Star.objects.count(), 1)

    def test_user_cannot_star_own_repo(self):
        self.client.login(username="owner", password="pass")
        url = reverse("repo_star", kwargs={"repo_id": self.public_repo.id})
        self.client.post(url, follow=True)
        self.assertEqual(Star.objects.count(), 0)

    def test_user_cannot_star_private_repo(self):
        self.client.login(username="other", password="pass")
        url = reverse("repo_star", kwargs={"repo_id": self.private_repo.id})
        self.client.post(url, follow=True)
        self.assertEqual(Star.objects.count(), 0)

    def test_admin_cannot_star(self):
        self.client.login(username="admin", password="pass")
        url = reverse("repo_star", kwargs={"repo_id": self.public_repo.id})
        self.client.post(url, follow=True)
        self.assertEqual(Star.objects.count(), 0)

    def test_star_is_unique(self):
        self.client.login(username="other", password="pass")
        url = reverse("repo_star", kwargs={"repo_id": self.public_repo.id})
        self.client.post(url, follow=True)
        self.client.post(url, follow=True)
        self.assertEqual(Star.objects.count(), 1)

    def test_unstar(self):
        self.client.login(username="other", password="pass")
        star_url = reverse("repo_star", kwargs={"repo_id": self.public_repo.id})
        unstar_url = reverse("repo_unstar", kwargs={"repo_id": self.public_repo.id})
        self.client.post(star_url, follow=True)
        self.assertEqual(Star.objects.count(), 1)
        self.client.post(unstar_url, follow=True)
        self.assertEqual(Star.objects.count(), 0)
