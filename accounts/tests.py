from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from registry.models import Repository, Star

User = get_user_model()


class SetupSystemCommandTests(TestCase):
    def test_creates_superadmin_and_writes_password_file(self):
        User = get_user_model()

        with TemporaryDirectory() as tmp:
            pass_file = Path(tmp) / "superadmin_password.txt"
            os.environ["SUPERADMIN_PASS_FILE"] = str(pass_file)
            os.environ["SUPERADMIN_USERNAME"] = "superadmin"
            os.environ["SUPERADMIN_EMAIL"] = "superadmin@example.com"

            call_command("setup_system")

            sa = User.objects.get(username="superadmin")
            self.assertEqual(sa.role, "SUPERADMIN")
            self.assertTrue(sa.must_change_password)

            self.assertTrue(pass_file.exists())
            password = pass_file.read_text(encoding="utf-8").strip()
            self.assertTrue(len(password) >= 12)

            # Password should work for login check
            self.assertTrue(sa.check_password(password))

    def test_idempotent_second_run_does_not_create_second_superadmin(self):
        User = get_user_model()

        with TemporaryDirectory() as tmp:
            pass_file = Path(tmp) / "superadmin_password.txt"
            os.environ["SUPERADMIN_PASS_FILE"] = str(pass_file)

            call_command("setup_system")
            call_command("setup_system")

            self.assertEqual(User.objects.filter(role="SUPERADMIN").count(), 1)

    def test_fails_if_password_file_env_missing(self):
        if "SUPERADMIN_PASS_FILE" in os.environ:
            del os.environ["SUPERADMIN_PASS_FILE"]

        with self.assertRaises(SystemExit):
            call_command("setup_system")


class MustChangePasswordMiddlewareTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="superadmin",
            password="TempPass123!",
            role="SUPERADMIN",
            must_change_password=True,
            is_staff=True,
            is_superuser=True,
        )

    def test_redirects_any_page_to_password_change(self):
        self.client.login(username="superadmin", password="TempPass123!")

        resp = self.client.get("/admin/", follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("password_change"), resp["Location"])

    def test_allows_password_change_page(self):
        self.client.login(username="superadmin", password="TempPass123!")

        resp = self.client.get(reverse("password_change"))
        self.assertEqual(resp.status_code, 200)

    def test_password_change_clears_flag(self):
        self.client.login(username="superadmin", password="TempPass123!")

        resp = self.client.post(
            reverse("password_change"),
            data={
                "old_password": "TempPass123!",
                "new_password1": "NewStrongPass123!",
                "new_password2": "NewStrongPass123!",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)

        # Now admin should be accessible
        resp2 = self.client.get("/admin/", follow=False)
        self.assertNotEqual(resp2.status_code, 302)


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role="ADMIN", must_change_password=False
        )
        # optional: make staff if you want them to use /admin/ too
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="pass12345", role="USER"
        )

    def test_non_admin_forbidden(self):
        self.client.login(username="alice", password="pass12345")
        resp = self.client.get(reverse("admin_user_list"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_open_list(self):
        self.client.login(username="admin1", password="pass12345")
        resp = self.client.get(reverse("admin_user_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "alice")

    def test_admin_can_set_publisher_status(self):
        self.client.login(username="admin1", password="pass12345")
        url = reverse("set_publisher_status", kwargs={"user_id": self.user.id})

        resp = self.client.post(url, data={"publisher_status": "VERIFIED_PUBLISHER"})
        self.assertEqual(resp.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.publisher_status, "VERIFIED_PUBLISHER")


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
