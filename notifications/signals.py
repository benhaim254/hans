import logging

from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from appointments.models import (STATUS_CANCELED, STATUS_DECLINED, STATUS_NO_SHOW, STATUS_PENDING, STATUS_PROPOSED,
                                 STATUS_SCHEDULED,
                                 Appointment)

from .models import Notification

logger = logging.getLogger(__name__)


def display_name(user):
    return user.get_full_name() or user.username


def notify(user, appointment, message):
    Notification.objects.create(user=user, appointment=appointment, message=message)
    if user.email:
        # Send after commit so a rolled-back booking never emails anyone.
        transaction.on_commit(lambda: send_email(user.email, message))


def send_email(address, message):
    # The notification row is already saved; a mail server outage must not turn the request into an error.
    try:
        send_mail('HANS appointment update', message, None, [address])
    except Exception:
        logger.exception('Could not email %s', address)


@receiver(pre_save, sender=Appointment)
def remember_previous_state(sender, instance, **kwargs):
    previous = (Appointment.objects.filter(pk=instance.pk)
                .values_list('status', 'appointment_date', 'appointment_time').first()
                if instance.pk else None)
    instance._previous_status, *instance._previous_time = previous or (None, None, None)


@receiver(post_save, sender=Appointment)
def notify_on_appointment_change(sender, instance, created, **kwargs):
    when = f"{instance.appointment_date:%a %d %b %Y} at {instance.appointment_time:%H:%M}"
    if created:
        notify(instance.patient, instance, f"Your appointment with Dr. {display_name(instance.doctor)} on {when} is awaiting confirmation.")
        notify(instance.doctor, instance, f"New appointment request from {display_name(instance.patient)} on {when}.")
        return

    previous = getattr(instance, '_previous_status', None)
    moved = getattr(instance, '_previous_time', None) != [instance.appointment_date, instance.appointment_time]
    # A reschedule, including back to the same time, returns the appointment to pending for the doctor.
    if instance.status == STATUS_PENDING and (moved or previous not in (None, STATUS_PENDING)):
        notify(instance.doctor, instance, f"{display_name(instance.patient)} moved their appointment to {when}. Please confirm the new time.")
        return
    if previous == instance.status:
        return
    if instance.status == STATUS_SCHEDULED and previous == STATUS_PROPOSED:
        notify(instance.doctor, instance, f"{display_name(instance.patient)} accepted the new time, {when}.")
    elif instance.status == STATUS_SCHEDULED:
        notify(instance.patient, instance, f"Dr. {display_name(instance.doctor)} confirmed your appointment on {when}.")
    elif instance.status == STATUS_DECLINED:
        notify(instance.patient, instance, f"Dr. {display_name(instance.doctor)} declined your request for {when}: {instance.cancellation_reason}")
    elif instance.status == STATUS_PROPOSED:
        notify(instance.patient, instance, f"Dr. {display_name(instance.doctor)} proposed a new time: {when}. Accept or decline it on your appointments page.")
    elif instance.status == STATUS_NO_SHOW:
        notify(instance.patient, instance, f"You were marked as missing your appointment with Dr. {display_name(instance.doctor)} on {when}.")
    elif instance.status == STATUS_CANCELED:
        notify(instance.doctor, instance, f"{display_name(instance.patient)} canceled the appointment on {when}.")
