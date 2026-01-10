from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# Create your models here.
class Appointment(models.Model):
    """
    Appointment model representing a scheduled meeting between patient and doctor.
    """

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("canceled", "Canceled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    )

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="patient_appointments",
        on_delete=models.CASCADE,
        limit_choices_to={"role": "patient"},
        help_text="Patient for this appointment.",
    )

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="doctor_appointments",
        on_delete=models.CASCADE,
        limit_choices_to={"role": "doctor"},
        help_text="Doctor for this appointment.",
    )

    start_time = models.DateTimeField(help_text="Appointment start time.")

    end_time = models.DateTimeField(help_text="Appointment end time.")

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current status of the appointment.",
    )

    reason = models.TextField(blank=True, help_text="Reason for the appointment.")

    notes = models.TextField(
        blank=True, help_text="Additional notes for the appointment."
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the appointment was created."
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When the appointment was last updated."
    )

    class Meta:
        db_table = "appointments"
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["doctor", "start_time"]),
            models.Index(fields=["patient", "start_time"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Appointment({self.patient} with {self.doctor} on {self.start_time})"

    def clean(self):
        """
        Validate appointment data before saving.
        """
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")
            if self.start_time < timezone.now():
                raise ValidationError("Start time cannot be in the past.")

        if self.patient_id == self.doctor_id:
            raise ValidationError("Patient and doctor cannot be the same user.")

    def save(self, *args, **kwargs):
        """
        Override save to run validation.
        """
        self.clean()
        super().save(*args, **kwargs)

    @property
    def duration(self):
        """
        Calculate appointment duration in minutes
        """
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def is_upcoming(self):
        """
        Check if the appointment is upcoming.
        """
        return self.start_time > timezone.now()

    @property
    def is_past(self):
        """
        Check if the appointment is in the past.
        """
        return self.end_time < timezone.now()

    def can_cancel(self):
        """
        Check if appointment can be cancelled.
        """
        return self.status in ["pending", "confirmed"] and self.is_upcoming

    def cancel(self):
        """
        Cancel the appointment if possible.
        """
        if self.can_cancel():
            self.status = "canceled"
            self.save()
            return True
        return False
