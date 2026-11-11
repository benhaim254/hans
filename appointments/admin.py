from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Appointment, TimeOff, WorkingHours


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
    list_display = (
        'patient', 
        'doctor', 
        'appointment_date', 
        'appointment_time',
        'duration_minutes',
        'status')
    list_filter = ('status', 'appointment_date')
    exclude = ('visit_notes',)  # private to the treating doctor
    search_fields = ('patient__username', 'doctor__username')

@admin.register(WorkingHours)
class WorkingHoursAdmin(ModelAdmin):
    list_display = ('doctor', 'weekday', 'start_time', 'end_time')
    list_filter = ('weekday',)
    search_fields = ('doctor__username',)


@admin.register(TimeOff)
class TimeOffAdmin(ModelAdmin):
    list_display = ('doctor', 'start_date', 'end_date', 'reason')
    search_fields = ('doctor__username',)
