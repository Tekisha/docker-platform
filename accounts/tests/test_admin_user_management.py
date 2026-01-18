from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from accounts.permissions import setup_groups_and_permissions, assign_user_to_group

User = get_user_model()


class AdminUserManagementTests(TestCase):
    def setUp(self):
        # Set up groups and permissions first
        setup_groups_and_permissions()
        
        self.admin = User.objects.create_user(
            username="admin1", password="pass12345", role="ADMIN", must_change_password=False
        )
        # optional: make staff if you want them to use /admin/ too
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        assign_user_to_group(self.admin)

        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="pass12345", role="USER"
        )
        assign_user_to_group(self.user)

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
