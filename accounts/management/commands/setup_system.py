from __future__ import annotations

import os
import secrets
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.permissions import setup_groups_and_permissions, assign_user_to_group


def generate_password(length: int = 24) -> str:
    """
    Generates a strong random password. URL-safe and copy/paste friendly.
    """
    # token_urlsafe(n) returns a string ~ 1.33*n chars; we trim to length
    return secrets.token_urlsafe(32)[:length]


def write_secret_file(path: Path, content: str) -> None:
    """
    Writes secret to file with best-effort safe permissions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create file atomically
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content + "\n", encoding="utf-8")

    tmp_path.replace(path)


class Command(BaseCommand):
    help = "Initial system setup: creates groups/permissions and SUPERADMIN. Optionally flushes database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush database before setup (default: False).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from django.core.management import call_command
        User = get_user_model()

        # Optionally flush the database first
        if options.get('flush'):
            self.stdout.write("Flushing database...")
            call_command('flush', '--noinput')
            self.stdout.write(self.style.SUCCESS("Database flushed."))

        # Set up groups and permissions first
        self.stdout.write("Setting up groups and permissions...")
        setup_groups_and_permissions()
        self.stdout.write(self.style.SUCCESS("Groups and permissions configured."))

        # Check if superadmin already exists (if not flushing)
        existing_superadmin = User.objects.filter(role="SUPERADMIN").first()
        if existing_superadmin and not options.get('flush'):
            # Still need to assign existing users to groups
            self.stdout.write("Assigning existing users to groups...")
            for user in User.objects.all():
                assign_user_to_group(user)
            self.stdout.write(self.style.SUCCESS("Setup already completed: SUPERADMIN exists. User groups updated."))
            return

        # Create SUPERADMIN
        pass_file = os.getenv("SUPERADMIN_PASS_FILE")
        if not pass_file:
            raise SystemExit(
                "SUPERADMIN_PASS_FILE is not set. "
                "Set it to a path where the generated password will be written (e.g. ./secrets/superadmin_password.txt)."
            )

        username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
        email = os.getenv("SUPERADMIN_EMAIL", "superadmin@example.com")

        # Check for username conflicts
        if User.objects.filter(username=username).exists():
            if not options.get('flush'):
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
        user.is_staff = True
        user.is_superuser = True
        user.save()

        # Assign user to appropriate group
        assign_user_to_group(user)

        # Write password to file (do not overwrite if file already exists)
        write_secret_file(Path(pass_file), password)

        self.stdout.write(self.style.SUCCESS("SUPERADMIN created."))
        self.stdout.write(self.style.SUCCESS(f"Username: {username}"))
        self.stdout.write(self.style.WARNING(f"Password written to: {pass_file}"))
        self.stdout.write(self.style.WARNING("Superadmin must change password on first login (must_change_password=True)."))
