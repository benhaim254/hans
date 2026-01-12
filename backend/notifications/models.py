from django.conf import settings
from django.db import models
from django.utils import timezone


# Create your models here.
class Notification(models.Model):
    """
    Notification model for sending alerts via various channels
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("push", "Push Notification"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    ]

    NOTIFICATION_TYPE_CHOICES = (
        ("appointment_confirmation", "Appointment Confirmation"),
        ("appointment_reminder", "Appointment Reminder"),
        ("appointment_cancellation", "Appointment Cancellation"),
        ("appointment_update", "Appointment Update"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User to recieve this notification",
    )

    channel = models.CharField(
        max_length=8,
        choices=CHANNEL_CHOICES,
        help_text="Delivery channel for notification",
    )

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="Related appointment (if applicable)",
    )

    notification_type = models.CharField(
        max_length=32,
        choices=NOTIFICATION_TYPE_CHOICES,
        default="appointment_confirmation",
        help_text="Type of notification being sent",
    )

    subject = models.CharField(
        max_length=200, blank=True, help_text="Notification subject (for email)"
    )

    message = models.TextField(help_text="Notification message content")

    payload = models.JSONField(
        default=dict, blank=True, help_text="Additional data for notification"
    )

    scheduled_at = models.DateTimeField(
        null=True, blank=True, help_text="Additional data for the notification"
    )

    sent_at = models.DateTimeField(
        null=True, blank=True, help_text="When notification was sent"
    )

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="scheduled",
        help_text="Current status of the notification",
    )

    error_message = models.TextField(
        blank=True, help_text="Error message if sending failed"
    )

    retry_count = models.IntegerField(
        default=0, help_text="Number of retry attempts for sending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the notification was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When the notification was last updated"
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["appointment", "status"]),
            models.Index(fields=["scheduled_at", "status"]),
            models.Index(fields=["channel", "status"]),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} to {self.user.username} - {self.get_status_display()}"

    def mark_as_sent(self):
        """
        Mark notification as successfully sent.
        """
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def can_retry(self, max_retries=3):
        """
        Check if notification can be retried.
        """
        return self.status == "failed" and self.retry_count < max_retries

    @property
    def is_due(self):
        """
        Check if notification is due to be sent.
        """
        if not self.scheduled_at:
            return True
        return self.scheduled_at <= timezone.now()
