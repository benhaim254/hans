from django.urls import path
from . import views

urlpatterns = [
    path('', views.patient_dashboard, name='patient_dashboard'),
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('confirm/<int:appointment_id>/', views.confirm_appointment, name='confirm_appointment'),
]