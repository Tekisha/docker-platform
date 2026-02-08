import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

@pytest.mark.django_db
def test_only_superadmin_can_access_page(client, superadmin_user, admin_user, regular_user):
    url = reverse("create_admin")

    # Regular user should not have access
    client.login(username="alice", password="pass12345")
    assert client.get(url).status_code == 403

    # Admin should not have access
    client.login(username="admin1", password="pass12345")
    assert client.get(url).status_code == 403

    # Superadmin should have access
    client.login(username="superadmin", password="pass12345!")
    assert client.get(url).status_code == 200

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
