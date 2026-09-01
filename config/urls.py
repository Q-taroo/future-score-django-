from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),  # raw DB inspection for ADMIN-role users (bonus, spec §24 helper)
    path("admin-panel/", include("adminpanel.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("scoring.urls")),
    path("", include("predictions.urls")),
]
