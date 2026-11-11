from django.urls import path

from . import views

urlpatterns = [
    path('', views.patient_dashboard, name='patient_dashboard'),
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/availability/', views.availability, name='availability'),
    path('<uuid:appointment_id>/confirm/', views.confirm_appointment, name='confirm_appointment'),
    path('<uuid:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
]
