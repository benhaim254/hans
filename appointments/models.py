from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from users.models import ROLE_DOCTOR, ROLE_PATIENT

STATUS_PENDING = 'pending'
STATUS_SCHEDULED = 'scheduled'
STATUS_COMPLETED = 'completed'
STATUS_CANCELED = 'canceled'

STATUS_TYPES = [
    (STATUS_PENDING, 'Pending'),
    (STATUS_SCHEDULED, 'Scheduled'),
    (STATUS_COMPLETED, 'Completed'),
    (STATUS_CANCELED, 'Canceled'),
]

CANCELABLE_STATUSES = (STATUS_PENDING, STATUS_SCHEDULED)


class Appointment(models.Model):

    appointment_id = models.UUIDField(default=uuid4, unique=True)

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
        limit_choices_to={'role': ROLE_PATIENT})

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_appointments',
        limit_choices_to={'role': ROLE_DOCTOR})

    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_TYPES,
        default=STATUS_PENDING)

    cancellation_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        constraints = [
            # A canceled booking frees the slot, so only active bookings must be unique.
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'appointment_time'],
                condition=~Q(status=STATUS_CANCELED),
                name='unique_active_doctor_slot',
            ),
        ]

    def __str__(self):
        return (f"Appointment: {self.patient} with Dr.{self.doctor} "
                f"on {self.appointment_date} at {self.appointment_time}")

    def clean(self):
        """Booking rules shared by the HTML form and the API serializer."""
        if self._state.adding and self.appointment_date and self.appointment_date < timezone.localdate():
            raise ValidationError({'appointment_date': 'Appointments cannot be booked in the past.'})

        if self.doctor_id and self.appointment_date and self.appointment_time:
            clash = (Appointment.objects
                     .filter(doctor_id=self.doctor_id,
                             appointment_date=self.appointment_date,
                             appointment_time=self.appointment_time)
                     .exclude(status=STATUS_CANCELED)
                     .exclude(pk=self.pk))
            if clash.exists():
                raise ValidationError('This doctor is already booked at that date and time.')

    def confirm(self):
        if self.status != STATUS_PENDING:
            raise ValidationError('Only pending appointments can be confirmed.')
        self.status = STATUS_SCHEDULED
        self.save(update_fields=['status', 'last_updated'])

    def cancel(self, reason):
        if self.status not in CANCELABLE_STATUSES:
            raise ValidationError('Only pending or scheduled appointments can be canceled.')
        self.status = STATUS_CANCELED
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_reason', 'last_updated'])
