from django.urls import path

from predictions import views

app_name = "predictions"

urlpatterns = [
    path("tutorial/", views.tutorial, name="tutorial"),
    path("", views.home, name="home"),
    path("predictions/", views.prediction_list, name="list"),
    path("predictions/<slug:slug>/", views.prediction_detail, name="detail"),
    path("predictions/vote/<slug:slug>/", views.vote, name="vote"),
]
