from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    HANS Custom User Model.
    Extends AbstractUser to allow for role-based access control (RBAC).

    Roles:
    Patient: Can book appointments.
    Doctor: View assigned appointments and set availability.
    Admin: System maintenance and staff management
    """
    # Assign labels to avoid confusion in views later
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
    Doesn't have a dedicated database table
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
# Adds a field to allow the user to distinguish their gender. 
# Other is the default for any who prefer not to say.
    gender = models.CharField(max_length=10,
                          choices=GENDER_CHOICES,
                          blank=True,
                          default=GENDER_OTHER)
# Date of birth is information that might be vital in some diagnosis. 
    date_of_birth = models.DateField(blank=True, null=True)
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

    BLOOD_A_POS = 'A+'
    BLOOD_A_NEG = 'A-'
    BLOOD_B_POS = 'B+'
    BLOOD_B_NEG = 'B-'
    BLOOD_AB_POS = 'AB+'
    BLOOD_AB_NEG = 'AB-'
    BLOOD_O_POS = 'O+'
    BLOOD_O_NEG = 'O-'

    BLOOD_GROUP_CHOICES = [
        (BLOOD_A_POS, 'A+'),
        (BLOOD_A_NEG, 'A-'),
        (BLOOD_B_POS, 'B+'),
        (BLOOD_B_NEG, 'B-'),
        (BLOOD_AB_POS, 'AB+'),
        (BLOOD_AB_NEG, 'AB-'),
        (BLOOD_O_POS, 'O+'),
        (BLOOD_O_NEG, 'O-'),
    ]

    blood_group = models.CharField(max_length=3,
                                   choices=BLOOD_GROUP_CHOICES,
                                   blank=True)
    allergies = models.TextField(blank=True,
                                 help_text="Please list any known allergies.")
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20,
                                               blank=True,
                                               help_text="Use international format: +254")

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
    specialization = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True, help_text="KMPDC license number")
    available_days= models.CharField(max_length=100, blank=True, help_text="e.g Mon, Wed, Fri")
    
    class Meta:
        verbose_name = 'Doctor Profile'
    
    def __str__(self):
        return f"Dr. {self.user.username} - {self.department}"