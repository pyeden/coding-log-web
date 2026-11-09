import os
import secrets
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the admin user and write credentials to .admin_credentials."

    def handle(self, *args, **options):
        username = os.environ.get("ORDER_ADMIN_USER", "admin")
        password = os.environ.get("ORDER_ADMIN_PASSWORD")
        generated = False
        if not password:
            password = secrets.token_urlsafe(12)
            generated = True

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        base_dir = Path(__file__).resolve().parents[3]
        cred_path = base_dir / ".admin_credentials"
        cred_path.write_text(
            f"username={username}\npassword={password}\n"
            f"url=https://seres-ai.com/order-admin/\n",
            encoding="utf-8",
        )
        cred_path.chmod(0o600)

        action = "created" if created else "password reset"
        self.stdout.write(
            self.style.SUCCESS(
                f"admin {action}: {username} (generated={generated}); credentials={cred_path}"
            )
        )
        self.stdout.write(f"admin_password={password}")
