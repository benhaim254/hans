from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class User(AbstractUser):
    """
    Custom user model for HANS.
    Extends Django's AbstractUser to add role-based access and additional fields.
    """

    ROLES = (
        ("patient", "Patient"),
        ("doctor", "Doctor"),
        ("admin", "Admin"),
    )

    role = models.CharField(
        max_length=16,
        choices=ROLES,
        default="patient",
        help_text="User role in the system",
    )

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_patient(self):
        return self.role == "patient"

    @property
    def is_doctor(self):
        return self.role == "doctor"

    @property
    def is_admin_user(self):
        return self.role == "admin"
