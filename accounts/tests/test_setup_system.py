from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

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

            # First run creates superadmin
            call_command("setup_system")
            
            # Second run should be idempotent (no flush in tests)
            call_command("setup_system")

            # Should have exactly one superadmin
            self.assertEqual(User.objects.filter(role="SUPERADMIN").count(), 1)

    def test_fails_if_password_file_env_missing(self):
        if "SUPERADMIN_PASS_FILE" in os.environ:
            del os.environ["SUPERADMIN_PASS_FILE"]

        with self.assertRaises(SystemExit):
            call_command("setup_system")
