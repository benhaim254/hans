from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ROLE_DOCTOR, ROLE_PATIENT, DoctorProfile, PatientProfile, User


@receiver(post_save, sender=User)
def sync_user_profile(sender, instance, created, update_fields=None, **kwargs):
    """
    Give each user the profile their role needs, on sign-up and when an admin changes the role.
    A user who stops being a doctor releases their KMPDC number so it can't stay locked to them.
    """
    if not created and update_fields is not None and 'role' not in update_fields:
        return  # e.g. the last_login update on every login
    if instance.role == ROLE_PATIENT:
        PatientProfile.objects.get_or_create(user=instance)
    elif instance.role == ROLE_DOCTOR:
        DoctorProfile.objects.get_or_create(user=instance)
    if not created and instance.role != ROLE_DOCTOR:
        DoctorProfile.objects.filter(user=instance, kmpdc__isnull=False).update(kmpdc=None)
