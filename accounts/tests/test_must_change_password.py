from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.fixture
def user_must_change_password(db, user_factory):
    user = user_factory(
        username="superadmin",
        password="TempPass123!",
        role="SUPERADMIN",
        must_change_password=True,
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.mark.django_db
def test_redirects_any_page_to_password_change(client, user_must_change_password):
    client.login(username="superadmin", password="TempPass123!")

    resp = client.get("/admin/", follow=False)
    assert resp.status_code == 302
    assert reverse("password_change") in resp["Location"]


@pytest.mark.django_db
def test_allows_password_change_page(client, user_must_change_password):
    client.login(username="superadmin", password="TempPass123!")

    resp = client.get(reverse("password_change"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_password_change_clears_flag(client, user_must_change_password):
    client.login(username="superadmin", password="TempPass123!")

    resp = client.post(
        reverse("password_change"),
        data={
            "old_password": "TempPass123!",
            "new_password1": "NewStrongPass123!",
            "new_password2": "NewStrongPass123!",
        },
        follow=True,
    )
    assert resp.status_code == 200

    user_must_change_password.refresh_from_db()
    assert not user_must_change_password.must_change_password

    # Now admin should be accessible
    resp2 = client.get("/admin/", follow=False)
    assert resp2.status_code != 302
