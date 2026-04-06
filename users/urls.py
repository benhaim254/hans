from django.urls import path
from . import views
from .views import RegisterView


app_name = 'users'

urlpatterns = [
    # home page for users app, lists all users
    path('', views.index, name='index'),
    path('register/', RegisterView.as_view(), name='register'),
]