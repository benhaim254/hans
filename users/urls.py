from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # home page for users app, lists all users
    path('', views.index, name='index'),
]