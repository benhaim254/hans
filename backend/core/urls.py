from django.urls import path

from . import views  # You'll need this soon!

# This variable name MUST be exactly 'urlpatterns'
urlpatterns = [
    # Leave this empty for now or add a dummy path:
    # path('', views.home, name='home'),
    path("secret/", views.secret, name="secret"),
]
