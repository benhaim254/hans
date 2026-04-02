from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, PatientProfile, DoctorProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **Kwargs):
    """
    Automatically creates a PatientProfile or DoctorProfile
    when a new User is created, based on their role.
    """

    if created:
        if instance.role == User.ROLE_PATIENT:
            PatientProfile.objects.create(user=instance)
        elif instance.role == User.ROLE_DOCTOR:
            DoctorProfile.objects.create(user=instance)