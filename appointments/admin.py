from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
    list_display = (
        'patient', 
        'doctor', 
        'appointment_date', 
        'appointment_time', 
        'status')
    list_filter = ('status', 'appointment_date')
    search_fields = ('patient__username', 'doctor__username')