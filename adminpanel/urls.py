from django.urls import path

from adminpanel import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("predictions/create/", views.create_prediction_view, name="create_prediction"),
    path("predictions/<int:prediction_id>/resolve/", views.resolve_view, name="resolve"),
    path("predictions/<int:prediction_id>/cancel/", views.cancel_prediction_view, name="cancel"),
    path("users/<int:user_id>/toggle-active/", views.toggle_user_active_view, name="toggle_user_active"),
]
