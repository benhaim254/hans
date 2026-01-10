from django.contrib import admin

from .models import Appointment


# Register your models here.
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin interface for the Appointment model.
    """

    list_display = [
        "id",
        "patient",
        "doctor",
        "start_time",
        "end_time",
        "status",
        "created_at",
    ]

    list_filter = [
        "status",
        "start_time",
        "created_at",
        "doctor",
    ]

    search_fields = [
        "patient__username",
        "patient__email",
        "doctor__username",
        "doctor__email",
        "reason",
    ]

    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Appointment Details",
            {"fields": ("patient", "doctor", "start_time", "end_time", "status")},
        ),
        ("Additional Information", {"fields": ("reason", "notes")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    date_hierarchy = "start_time"

    def get_queryset(self, request):
        """
        Customize the queryset to prefetch related patient and doctor data.
        """
        qs = super().get_queryset(request)
        return qs.select_related("patient", "doctor")
