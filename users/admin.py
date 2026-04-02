from django.contrib import admin
from .models import User, DoctorProfile, PatientProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']
    list_filter = ['role']  
    search_fields = ['username', 'email']

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'gender', 'phone', 
                    'date_of_birth', 'blood_group']
    list_filter = ['gender','blood_group']
    search_fields = ['user__username']

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['user','gender', 'phone', 
                    'date_of_birth', 'department', 
                    'specialization', 'license_number']       
    list_filter = ['gender', 'department']
    search_fields = ['user__username', 'license_number']

