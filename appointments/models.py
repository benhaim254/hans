from datetime import datetime, time, timedelta
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F, Q
from django.utils import timezone

from users.models import ROLE_DOCTOR, ROLE_PATIENT

STATUS_PENDING = 'pending'
STATUS_SCHEDULED = 'scheduled'
STATUS_COMPLETED = 'completed'
STATUS_CANCELED = 'canceled'
STATUS_NO_SHOW = 'no_show'
STATUS_DECLINED = 'declined'
STATUS_PROPOSED = 'proposed'

STATUS_TYPES = [
    (STATUS_PENDING, 'Pending'),
    (STATUS_SCHEDULED, 'Scheduled'),
    (STATUS_COMPLETED, 'Completed'),
    (STATUS_CANCELED, 'Canceled'),
    (STATUS_NO_SHOW, 'No-show'),
    (STATUS_DECLINED, 'Declined'),
    (STATUS_PROPOSED, 'New time proposed'),
]

CANCELABLE_STATUSES = (STATUS_PENDING, STATUS_SCHEDULED, STATUS_PROPOSED)
# Appointments in these statuses no longer hold their time slot.
INACTIVE_STATUSES = (STATUS_CANCELED, STATUS_DECLINED)

DOUBLE_BOOKED_MESSAGE = 'This doctor is already booked at that date and time.'

WEEKDAYS = [
    (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
    (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
]

SLOT_STEP_MINUTES = 15


class WorkingHours(models.Model):
    """One working range per doctor per weekday. No row means the doctor is off that day."""
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='working_hours', limit_choices_to={'role': ROLE_DOCTOR})
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['weekday']
        verbose_name_plural = 'working hours'
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'weekday'], name='one_range_per_doctor_weekday'),
            models.CheckConstraint(condition=Q(end_time__gt=F('start_time')), name='working_hours_end_after_start'),
        ]

    def __str__(self):
        return f"{self.doctor.username}: {self.get_weekday_display()} {self.start_time:%H:%M} to {self.end_time:%H:%M}"


class TimeOff(models.Model):
    """Dates a doctor is away (leave, conferences). No bookings on these days."""
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='time_off', limit_choices_to={'role': ROLE_DOCTOR})
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['start_date']
        verbose_name_plural = 'time off'
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F('start_date')), name='time_off_end_not_before_start'),
        ]

    def __str__(self):
        return f"{self.doctor.username}: {self.start_date} to {self.end_date}"


def on_leave(doctor_id, day):
    return TimeOff.objects.filter(doctor_id=doctor_id, start_date__lte=day, end_date__gte=day).exists()


def _add_minutes(at, minutes):
    return (datetime.combine(datetime.min, at) + timedelta(minutes=minutes)).time()


def _busy_ranges(doctor_id, day, exclude_pk=None):
    """(start, end) times already taken by the doctor's active appointments on that day."""
    taken = (Appointment.objects
             .filter(doctor_id=doctor_id, appointment_date=day)
             .exclude(status__in=INACTIVE_STATUSES)
             .exclude(pk=exclude_pk)
             .values_list('appointment_time', 'duration_minutes'))
    return [(start, _add_minutes(start, minutes)) for start, minutes in taken]


def _overlaps(start, end, busy):
    return any(start < busy_end and end > busy_start for busy_start, busy_end in busy)


def available_slots(doctor, day):
    """Start times on a 15-minute grid where a full appointment fits and nothing overlaps."""
    hours = doctor.working_hours.filter(weekday=day.weekday()).first()
    today = timezone.localdate()
    if hours is None or day < today or on_leave(doctor.pk, day):
        return []
    length = doctor.doctorprofile.appointment_length
    busy = _busy_ranges(doctor.pk, day)
    now = timezone.localtime().time() if day == today else None
    open_at = hours.start_time.hour * 60 + hours.start_time.minute
    close_at = hours.end_time.hour * 60 + hours.end_time.minute
    slots = []
    for minute in range(open_at, close_at - length + 1, SLOT_STEP_MINUTES):
        start = time(minute // 60, minute % 60)
        if (now is None or start > now) and not _overlaps(start, _add_minutes(start, length), busy):
            slots.append(start)
    return slots


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
    # Copied from the doctor's profile at booking, so later changes don't move existing appointments.
    duration_minutes = models.PositiveSmallIntegerField(default=30)
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
            # Database backstop: SQLite can't reject overlapping ranges, but it can reject identical starts.
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'appointment_time'],
                condition=~Q(status__in=INACTIVE_STATUSES),
                name='unique_active_doctor_slot',
            ),
        ]

    def __str__(self):
        return (f"Appointment: {self.patient} with Dr.{self.doctor} "
                f"on {self.appointment_date} at {self.appointment_time}")

    @property
    def has_started(self):
        starts_at = timezone.make_aware(datetime.combine(self.appointment_date, self.appointment_time))
        return starts_at <= timezone.now()

    @property
    def end_time(self):
        return _add_minutes(self.appointment_time, self.duration_minutes)

    def _take_doctor_length(self):
        if self._state.adding and self.doctor_id and hasattr(self.doctor, 'doctorprofile'):
            self.duration_minutes = self.doctor.doctorprofile.appointment_length

    def save(self, *args, **kwargs):
        self._take_doctor_length()
        super().save(*args, **kwargs)

    def clean(self):
        """Booking rules shared by the HTML form and the API serializer."""
        if not (self.doctor_id and self.appointment_date and self.appointment_time):
            return
        self._take_doctor_length()

        if self._state.adding:
            self._check_new_time()
        self._check_free()

    def _check_new_time(self):
        """Rules for any newly chosen time: future, not on leave, a working day, inside the hours."""
        if self.appointment_date < timezone.localdate():
            raise ValidationError({'appointment_date': 'Appointments cannot be booked in the past.'})
        if self.has_started:
            raise ValidationError({'appointment_time': 'That time has already passed.'})
        if on_leave(self.doctor_id, self.appointment_date):
            raise ValidationError({'appointment_date': 'The doctor is on leave that day.'})
        hours = self.doctor.working_hours.filter(weekday=self.appointment_date.weekday()).first()
        if hours is None:
            raise ValidationError({'appointment_date': "The doctor doesn't work on that day."})
        if self.appointment_time < hours.start_time or self.end_time > hours.end_time:
            raise ValidationError({'appointment_time': (
                f"A {self.duration_minutes}-minute appointment must fit between "
                f"{hours.start_time:%H:%M} and {hours.end_time:%H:%M}.")})

    def _check_free(self):
        busy = _busy_ranges(self.doctor_id, self.appointment_date, exclude_pk=self.pk)
        if _overlaps(self.appointment_time, self.end_time, busy):
            raise ValidationError(DOUBLE_BOOKED_MESSAGE)

    def _move_to(self, day, at, status):
        """Move to a new time after checking every booking rule; the old time is freed."""
        old = (self.appointment_date, self.appointment_time)
        self.appointment_date, self.appointment_time = day, at
        old_status = self.status
        try:
            self._check_new_time()
            self._check_free()
            self.status = status
            with transaction.atomic():
                self.save(update_fields=['appointment_date', 'appointment_time', 'status', 'last_updated'])
        except (ValidationError, IntegrityError) as error:
            self.appointment_date, self.appointment_time = old
            self.status = old_status
            if isinstance(error, IntegrityError):  # someone took the slot between the check and the save
                raise ValidationError(DOUBLE_BOOKED_MESSAGE)
            raise

    def decline(self, reason):
        if self.status != STATUS_PENDING:
            raise ValidationError('Only pending requests can be declined.')
        self.status = STATUS_DECLINED
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_reason', 'last_updated'])

    def propose(self, day, at):
        if self.status != STATUS_PENDING:
            raise ValidationError('You can only propose a new time for a pending request.')
        self._move_to(day, at, STATUS_PROPOSED)

    def reschedule(self, day, at):
        """Patient moves their own appointment; the doctor has to confirm the new time."""
        if self.status not in CANCELABLE_STATUSES:
            raise ValidationError('Only upcoming appointments can be rescheduled.')
        self._move_to(day, at, STATUS_PENDING)

    def accept_proposal(self):
        if self.status != STATUS_PROPOSED:
            raise ValidationError('There is no proposed time to accept.')
        self.status = STATUS_SCHEDULED
        self.save(update_fields=['status', 'last_updated'])

    def confirm(self):
        if self.status != STATUS_PENDING:
            raise ValidationError('Only pending appointments can be confirmed.')
        self.status = STATUS_SCHEDULED
        self.save(update_fields=['status', 'last_updated'])

    def _finish(self, status):
        if self.status != STATUS_SCHEDULED:
            raise ValidationError('Only scheduled appointments can be closed.')
        if not self.has_started:
            raise ValidationError("This appointment hasn't started yet.")
        self.status = status
        self.save(update_fields=['status', 'last_updated'])

    def complete(self):
        self._finish(STATUS_COMPLETED)

    def mark_no_show(self):
        self._finish(STATUS_NO_SHOW)

    def cancel(self, reason):
        if self.status not in CANCELABLE_STATUSES:
            raise ValidationError('Only upcoming appointments can be canceled.')
        self.status = STATUS_CANCELED
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_reason', 'last_updated'])
