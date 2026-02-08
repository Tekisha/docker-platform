from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from django.core.management import call_command
from django.contrib.auth import get_user_model



@pytest.mark.django_db
def test_creates_superadmin_and_writes_password_file():
    User = get_user_model()
    
    with TemporaryDirectory() as tmp:
        pass_file = Path(tmp) / "superadmin_password.txt"
        os.environ["SUPERADMIN_PASS_FILE"] = str(pass_file)
        os.environ["SUPERADMIN_USERNAME"] = "superadmin"
        os.environ["SUPERADMIN_EMAIL"] = "superadmin@example.com"

        call_command("setup_system")

        sa = User.objects.get(username="superadmin")
        assert sa.role == "SUPERADMIN"
        assert sa.must_change_password

        assert pass_file.exists()
        password = pass_file.read_text(encoding="utf-8").strip()
        assert len(password) >= 12

        # Password should work for login check
        assert sa.check_password(password)


@pytest.mark.django_db
def test_idempotent_second_run_does_not_create_second_superadmin():
    User = get_user_model()
    
    with TemporaryDirectory() as tmp:
        pass_file = Path(tmp) / "superadmin_password.txt"
        os.environ["SUPERADMIN_PASS_FILE"] = str(pass_file)

        call_command("setup_system")
        call_command("setup_system")

        assert User.objects.filter(role="SUPERADMIN").count() == 1


@pytest.mark.django_db
def test_fails_if_password_file_env_missing():
    if "SUPERADMIN_PASS_FILE" in os.environ:
        del os.environ["SUPERADMIN_PASS_FILE"]

    with pytest.raises(SystemExit):
        call_command("setup_system")
