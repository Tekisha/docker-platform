from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class SuperadminCreateAdminTests(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_user(
            username="superadmin",
            password="pass12345!",
            role="SUPERADMIN",
            must_change_password=False,
        )
        self.superadmin.is_staff = True
        self.superadmin.is_superuser = True
        self.superadmin.save(update_fields=["is_staff", "is_superuser"])

        self.admin = User.objects.create_user(
            username="admin1",
            password="pass12345!",
            role="ADMIN",
            must_change_password=False,
        )
        self.user = User.objects.create_user(
            username="alice",
            password="pass12345!",
            role="USER",
        )

    def test_only_superadmin_can_access_page(self):
        url = reverse("create_admin")

        self.client.login(username="alice", password="pass12345!")
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.login(username="admin1", password="pass12345!")
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.login(username="superadmin", password="pass12345!")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_superadmin_can_create_admin(self):
        self.client.login(username="superadmin", password="pass12345!")
        url = reverse("create_admin")

        resp = self.client.post(url, data={
            "username": "newadmin",
            "email": "newadmin@example.com",
            "temp_password": "TempPass123!",
        }, follow=True)

        self.assertEqual(resp.status_code, 200)

        u = User.objects.get(username="newadmin")
        self.assertEqual(u.role, "ADMIN")
        self.assertTrue(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertTrue(u.must_change_password)
        self.assertTrue(u.check_password("TempPass123!"))
