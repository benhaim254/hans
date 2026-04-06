from django.urls import path
from . import views
from .views import RegisterView, PatientOnlyView, DoctorOnlyView


app_name = 'users'

urlpatterns = [
    # home page for users app, lists all users
    path('', views.index, name='index'),
    path('register/', RegisterView.as_view(), name='register'),
    path('patient-only/', PatientOnlyView.as_view(), name='patient_only'),
    path('doctor-only/', DoctorOnlyView.as_view(), name='doctor_only'),
]