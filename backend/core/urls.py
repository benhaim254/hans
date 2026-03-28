from django.urls import path

from . import views  # You'll need this soon!

urlpatterns = [
    path("", views.index),
    path("secret/", views.secret, name="secret"),
]
