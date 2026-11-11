from django.urls import path

from . import views

urlpatterns = [
    path('', views.patient_dashboard, name='patient_dashboard'),
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/availability/', views.availability, name='availability'),
    path('doctor/time-off/', views.add_time_off, name='add_time_off'),
    path('doctor/time-off/<int:pk>/delete/', views.delete_time_off, name='delete_time_off'),
    path('<uuid:appointment_id>/confirm/', views.confirm_appointment, name='confirm_appointment'),
    path('<uuid:appointment_id>/complete/', views.complete_appointment, name='complete_appointment'),
    path('<uuid:appointment_id>/no-show/', views.no_show_appointment, name='no_show_appointment'),
    path('<uuid:appointment_id>/respond/', views.respond_to_request, name='respond_to_request'),
    path('<uuid:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('<uuid:appointment_id>/accept/', views.accept_proposal, name='accept_proposal'),
    path('<uuid:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
]
