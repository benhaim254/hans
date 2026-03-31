from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    HANS Custom User Model.
    Extends AbstractUser to allow for role-based access control (RBAC).
    
    Roles:
    - Patient: Default user, can book appointments.
    - Doctor: Can view assigned appointments and set availability.
    - Admin: System oversight and staff management.
    """
    # Use Constants for roles to avoid "magic strings" in views later
    ROLE_PATIENT = 'patient'
    ROLE_DOCTOR = 'doctor'
    ROLE_ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (ROLE_PATIENT, 'Patient'),
        (ROLE_DOCTOR, 'Doctor'),
        (ROLE_ADMIN, 'Admin'),
    ]

# Add a role field to determine user type and permissions. Default role of user is 'patient'.
    role = models.CharField(max_length=10, 
                            choices=ROLE_CHOICES, 
                            default=ROLE_PATIENT)

# Needed for communication and Notifications. Setup for future SMS/Email integration.
    phone = models.CharField(max_length=20,
                             blank=True,
                             help_text="Use international format: +254")

#Return username and role for easy identification in admin and debugging.
    def __str__(self):
        return f"{self.username} ({self.role})"