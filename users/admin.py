from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import DoctorProfile, PatientProfile, User

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Built on Django's UserAdmin so passwords are hashed and changed through the proper form.
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    fieldsets = BaseUserAdmin.fieldsets + (('Role', {'fields': ('role',)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (('Role', {'fields': ('role',)}),)
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']


@admin.register(PatientProfile)
class PatientProfileAdmin(ModelAdmin):
    list_display = ['user', 'gender', 'phone_number',
                    'date_of_birth', 'blood_group']
    list_filter = ['gender', 'blood_group']
    search_fields = ['user__username']


@admin.register(DoctorProfile)
class DoctorProfileAdmin(ModelAdmin):
    list_display = ['user', 'gender', 'phone_number',
                    'date_of_birth', 'department',
                    'specialization', 'license_number']
    list_filter = ['gender', 'department']
    search_fields = ['user__username', 'license_number']
