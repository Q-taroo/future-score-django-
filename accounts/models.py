from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    """Custom user model (spec §24).

    Extends Django's AbstractUser (which already gives us username, email,
    password hashing, is_active, last_login, etc.) with the fields FUTURE
    SCORE needs: an explicit role for admin gating, and a bio for the
    public profile page.
    """

    class Role(models.TextChoices):
        USER = "USER", "USER"
        ADMIN = "ADMIN", "ADMIN"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    bio = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["role"])]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_email_ci_unique",
            )
        ]

    def __str__(self) -> str:
        return self.username

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    def save(self, *args, **kwargs):
        # Keep Django's own is_staff flag in sync with our role field, so
        # ADMIN users can also use /django-admin/ for raw data inspection
        # as a bonus without maintaining two separate permission systems.
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)
