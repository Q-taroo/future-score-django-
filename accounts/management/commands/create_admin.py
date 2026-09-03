import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update an admin from optional ADMIN_* environment variables."

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_EMAIL", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "")
        if not email or not password:
            self.stdout.write("create_admin skipped: ADMIN_EMAIL/ADMIN_PASSWORD not set")
            return

        User = get_user_model()
        username = os.environ.get("ADMIN_USERNAME", "admin").strip() or "admin"
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS("create_admin OK"))
