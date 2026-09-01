from django.urls import path

from scoring import views

app_name = "scoring"

urlpatterns = [
    path("ranking/", views.ranking, name="ranking"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("me/", views.me_dashboard, name="me_dashboard"),
]
