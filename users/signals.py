from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PatientProfile, DoctorProfile, ROLE_PATIENT, ROLE_DOCTOR

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a PatientProfile or DoctorProfile
    when a new User is created, based on their role.
    """

    if created:
        if instance.role == ROLE_PATIENT:
            PatientProfile.objects.create(user=instance)
        elif instance.role == ROLE_DOCTOR:
            DoctorProfile.objects.create(user=instance, department='general')