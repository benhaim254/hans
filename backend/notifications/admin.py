from django.contrib import admin
from django.utils.html import format_html

from .models import Notification


# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification model
    """

    list_display = [
        "id",
        "user",
        "channel",
        "notification_type",
        "status_badge",
        "scheduled_at",
        "sent_at",
        "retry_count",
    ]

    list_filter = [
        "status",
        "channel",
        "notification_type",
        "created_at",
        "scheduled_at",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "subject",
        "message",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "sent_at",
        "retry_count",
    ]

    fieldsets = (
        ("Recipient", {"fields": ("user", "channel")}),
        (
            "Notification Details",
            {"fields": ("notification_type", "appointment", "subject", "message")},
        ),
        (
            "Scheduling & Status",
            {
                "fields": (
                    "scheduled_at",
                    "status",
                    "sent_at",
                )
            },
        ),
        (
            "Error Handling",
            {"fields": ("error_message", "retry_count"), "classes": ("collapse",)},
        ),
        ("Additional Data", {"fields": ("payload",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    date_hierarchy = "created_at"

    def status_badge(self, obj):
        """
        Display status with color coding.
        """
        colors = {
            "scheduled": "blue",
            "sent": "green",
            "failed": "red",
            "canceled": "gray",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def get_queryset(self, request):
        """
        Optimize queries by selecting related user and appointment.
        """
        qs = super().get_queryset(request)
        return qs.select_related("user", "appointment")

    actions = ["mark_as_cancelled"]

    def mark_as_cancelled(self, request, queryset):
        """
        Bulk action to cancel scheduled notifications.
        """
        updated = queryset.filter(status="scheduled").update(status="canceled")
        self.message_user(request, f"{updated} notification(s) marked as canceled.")

    mark_as_cancelled.short_description = "Cancel selected scheduled notifications"
