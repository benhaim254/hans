from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    HANS Custom User Model.
    Extends AbstractUser to allow for role-based access control (RBAC).
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
# Add a role field to determine user type and permissions. 
# Default role of user is 'patient'.
    role = models.CharField(max_length=10, 
                            choices=ROLE_CHOICES, 
                            default=ROLE_PATIENT)
#Return username and role for easy identification in admin and debugging.
    def __str__(self):
        return f"{self.username} ({self.role})"
    
class CommonProfile(models.Model):
    """
    Contains fields shared by all profile types.
    """
    GENDER_MALE = 'male'
    GENDER_FEMALE = 'female'
    GENDER_OTHER = 'other'

    GENDER_CHOICES = [
        (GENDER_MALE, 'Male'),
        (GENDER_FEMALE, 'Female'),
        (GENDER_OTHER, 'Other')
    ]

    user = models.OneToOneField('User',on_delete=models.CASCADE)
# Add a role field to allow the user to distinguish their gender. 
# Other is the default for thoes who prefer not to say.
    gender = models.CharField(max_length=10,
                          choices=GENDER_CHOICES,
                          blank=True,
                          default=GENDER_OTHER)
# Needed for communication and Notifications. 
# Setup for future SMS/Email integration.
    phone = models.CharField(max_length=20,
                             blank=True,
                             help_text="Use international format: +254")
    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.user.username}"

class PatientProfile(CommonProfile):
    """
    Contains information about the patient.
    """
    class Meta:
        verbose_name = 'Patient Profile'
    
    def __str__(self):
        return f"Patient: {self.user.username}"

class DoctorProfile(CommonProfile):
    """
    Additional doctor information.
    """

    DEPT_GENERAL = 'general'
    DEPT_CARDIOLOGY = 'cardiology'
    DEPT_PEDIATRICS = 'pediatrics'
    DEPT_ORTHOPEDICS = 'orthopedics'
    DEPT_DERMATOLOGY = 'dermatology'

    DEPARTMENT_CHOICES = [
        (DEPT_GENERAL, 'General'),
        (DEPT_CARDIOLOGY, 'Cardiology'),
        (DEPT_PEDIATRICS, 'Pediatrics'),
        (DEPT_ORTHOPEDICS, 'Orthopedics'),
        (DEPT_DERMATOLOGY, 'Dermatology')
    ]

    

    department = models.CharField(max_length=20,choices=DEPARTMENT_CHOICES,
                                  default=DEPT_GENERAL)
    
    class Meta:
        verbose_name = 'Doctor Profile'
    
    def __str__(self):
        return f"Dr. {self.user.username} - {self.department}"