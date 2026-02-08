from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_non_admin_forbidden(client, regular_user):
    client.login(username="alice", password="pass12345")
    resp = client.get(reverse("admin_user_list"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_can_open_list(client, admin_user, regular_user):
    client.login(username="admin1", password="pass12345")
    resp = client.get(reverse("admin_user_list"))
    assert resp.status_code == 200
    assert "alice" in resp.content.decode()


@pytest.mark.django_db
def test_admin_can_set_publisher_status(client, admin_user, regular_user):
    client.login(username="admin1", password="pass12345")
    url = reverse("set_publisher_status", kwargs={"user_id": regular_user.id})

    resp = client.post(url, data={"publisher_status": "VERIFIED_PUBLISHER"})
    assert resp.status_code == 302

    regular_user.refresh_from_db()
    assert regular_user.publisher_status == "VERIFIED_PUBLISHER"
