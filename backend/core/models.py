from django.db import models


# Create your models here.
class User(models.Model):
    First_name = models.CharField(max_length=16)
    Last_name = models.CharField(max_length=16)
    email = models.EmailField(max_length=255)

    def __str__(self):
        return f"ID:{self.id}, Name: {self.First_name} {self.Last_name}, Email: {self.email}"
