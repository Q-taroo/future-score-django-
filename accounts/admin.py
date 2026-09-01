from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class FutureScoreUserAdmin(UserAdmin):
    """Raw data inspection for admins via /django-admin/ (bonus, spec
    §24) — reuses Django's battle-tested UserAdmin and just surfaces
    our extra `role` field alongside the built-in ones."""

    list_display = ("username", "email", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("FUTURE SCORE", {"fields": ("role", "bio")}),)
