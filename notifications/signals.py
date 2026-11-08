from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from appointments.models import STATUS_CANCELED, STATUS_SCHEDULED, Appointment

from .models import Notification


def display_name(user):
    return user.get_full_name() or user.username


def notify(user, appointment, message):
    Notification.objects.create(user=user, appointment=appointment, message=message)
    if user.email:
        # Send after commit so a rolled-back booking never emails anyone.
        transaction.on_commit(lambda: send_mail('HANS appointment update', message, None, [user.email]))


@receiver(pre_save, sender=Appointment)
def remember_previous_status(sender, instance, **kwargs):
    instance._previous_status = (
        Appointment.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        if instance.pk else None
    )


@receiver(post_save, sender=Appointment)
def notify_on_appointment_change(sender, instance, created, **kwargs):
    when = f"{instance.appointment_date:%a %d %b %Y} at {instance.appointment_time:%H:%M}"
    if created:
        notify(instance.patient, instance, f"Your appointment with Dr. {display_name(instance.doctor)} on {when} is awaiting confirmation.")
        notify(instance.doctor, instance, f"New appointment request from {display_name(instance.patient)} on {when}.")
        return

    previous = getattr(instance, '_previous_status', None)
    if previous == instance.status:
        return
    if instance.status == STATUS_SCHEDULED:
        notify(instance.patient, instance, f"Dr. {display_name(instance.doctor)} confirmed your appointment on {when}.")
    elif instance.status == STATUS_CANCELED:
        notify(instance.doctor, instance, f"{display_name(instance.patient)} canceled the appointment on {when}.")
