from django.contrib import admin
from .models import User, DoctorProfile, PatientProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'get_gender', 'get_phone']
    list_filter = ['role']  
    search_fields = ['username', 'email']

    @admin.display(description='Gender')
    def get_gender(self, obj):
        profile = getattr(obj, 'doctorprofile', None) or getattr(obj, 'patientprofile', None)
        return profile.gender if profile else '—'

    @admin.display(description='Phone')
    def get_phone(self, obj):
        profile = getattr(obj, 'doctorprofile', None) or getattr(obj, 'patientprofile', None)
        return profile.phone if profile else '—'

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department']       
    list_filter = ['department']
    search_fields = ['user__username']

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'gender', 'phone']
    list_filter = ['gender']
    search_fields = ['user__username']