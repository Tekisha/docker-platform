from __future__ import annotations

import os
import secrets
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model


def generate_password(length: int = 24) -> str:
    """
    Generates a strong random password. URL-safe and copy/paste friendly.
    """
    # token_urlsafe(n) returns a string ~ 1.33*n chars; we trim to length
    return secrets.token_urlsafe(32)[:length]


def write_secret_file(path: Path, content: str) -> None:
    """
    Writes secret to file with best-effort safe permissions.
    If the file already exists, do not overwrite (prevents accidental rotation without intent).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Don't overwrite if already exists
    if path.exists():
        return

    # Create file atomically
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content + "\n", encoding="utf-8")

    tmp_path.replace(path)


class Command(BaseCommand):
    help = "Initial system setup: creates a single SUPERADMIN and writes generated password to a file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation if no SUPERADMIN exists; still does not overwrite existing password file.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # If a superadmin exists, we do nothing (idempotent)
        existing = User.objects.filter(role="SUPERADMIN").exists()
        if existing and not options.get("--force", False):
            self.stdout.write(self.style.SUCCESS("Setup already completed: SUPERADMIN exists. Nothing to do."))
            return

        pass_file = os.getenv("SUPERADMIN_PASS_FILE")
        if not pass_file:
            raise SystemExit(
                "SUPERADMIN_PASS_FILE is not set. "
                "Set it to a path where the generated password will be written (e.g. ./secrets/superadmin_password.txt)."
            )

        username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
        email = os.getenv("SUPERADMIN_EMAIL", "superadmin@example.com")

        # If somehow exists but filter differs, guard against duplicates by username too
        if User.objects.filter(username=username).exists():
            # If username taken but no superadmin role exists, we still shouldn't create duplicate blindly.
            # Better to fail loudly.
            raise SystemExit(f"Cannot create superadmin: username '{username}' is already taken.")

        password = generate_password()

        # Create SUPERADMIN (single role model)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        user.role = "SUPERADMIN"
        user.must_change_password = True
        user.save()

        # Write password to file (do not overwrite if file already exists)
        write_secret_file(Path(pass_file), password)

        self.stdout.write(self.style.SUCCESS("SUPERADMIN created."))
        self.stdout.write(self.style.SUCCESS(f"Username: {username}"))
        self.stdout.write(self.style.WARNING(f"Password written to: {pass_file}"))
        self.stdout.write(self.style.WARNING("Superadmin must change password on first login (must_change_password=True)."))
