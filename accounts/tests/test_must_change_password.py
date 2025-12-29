from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

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
