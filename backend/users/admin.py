from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User

# Register your models here.


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.
    """

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name", "phone"]

    fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Additional Info", {"fields": ("role", "phone")}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Additional Info",
            {"fields": ("role", "phone", "email", "first_name", "last_name")},
        ),
    )
