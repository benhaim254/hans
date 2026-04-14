from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

ROLE_PATIENT = 'patient'
ROLE_DOCTOR = 'doctor'
ROLE_ADMIN = 'admin'

ROLE_TYPES = [
    ( ROLE_PATIENT , 'Patient'),
    ( ROLE_DOCTOR , 'Doctor'),
    ( ROLE_ADMIN , 'Admin'),
]

GENDER_TYPES = [
    ('Male', 'male'),
    ('Female', 'female'),
    ('Other', 'other')
]


BLOOD_GROUP_TYPES = [
    ('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('O+', 'O+'),
    ('O-', 'O-'),
]


DEPARTMENT_CHOICES = [
    ('DEPT_GENERAL', 'General'),
    ('DEPT_CARDIOLOGY', 'Cardiology'),
    ('DEPT_PEDIATRICS', 'Pediatrics'),
    ('DEPT_ORTHOPEDICS', 'Orthopedics'),
    ('DEPT_DERMATOLOGY', 'Dermatology')
]

    
    
class User(AbstractUser):
    """
    HANS Custom User Model.
    Extends AbstractUser to allow for role-based access control (RBAC).

    Roles:
    Patient: Can book appointments.
    Doctor: View assigned appointments and set availability.
    Admin: System maintenance and staff management
    """

# Add a role field to determine user type and permissions. 
# Default role of user is 'patient'.
    role = models.CharField(max_length=10, 
                            choices=ROLE_TYPES, 
                            default= ROLE_PATIENT)
#Return username and role for easy identification in admin and debugging.
    def __str__(self):
        return f"{self.username} ({self.role})"

    
class CommonProfile(models.Model):
    """
    Contains fields shared by all profile types.
    Doesn't have a dedicated database table
    """

    user = models.OneToOneField('User',on_delete=models.CASCADE)
# Adds a field to allow the user to distinguish their gender. 
# Other is the default for any who prefer not to say.
    gender = models.CharField(max_length=10,
                          choices=GENDER_TYPES,
                          blank=True)
# Date of birth is information that might be vital in some diagnosis. 
    date_of_birth = models.DateField(blank=True, null=True)
# Needed for communication and Notifications. 
# Setup for future SMS/Email integration.
    phone_number = PhoneNumberField(blank=True)
    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.user.username}"

class PatientProfile(CommonProfile):
    """
    Contains information about the patient.
    """
    blood_group = models.CharField(max_length=3,
                                   choices=BLOOD_GROUP_TYPES,
                                   blank=True)
    allergies = models.TextField(blank=True,
                                 help_text="Please list any known allergies.")
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone =  PhoneNumberField(blank=True)

    class Meta:
        verbose_name = 'Patient Profile'
    
    def __str__(self):
        return f"Patient: {self.user.username}"


class DoctorProfile(CommonProfile):
    """
    Additional doctor information.
    """    
    department = models.CharField(max_length=20,choices=DEPARTMENT_CHOICES)
    specialization = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True, help_text="KMPDC license number")
    available_days= models.CharField(max_length=100, blank=True, help_text="e.g Mon, Wed, Fri")
    
    class Meta:
        verbose_name = 'Doctor Profile'
    
    def __str__(self):
        return f"Dr. {self.user.username} - {self.department}"