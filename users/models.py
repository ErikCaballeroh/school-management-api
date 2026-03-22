from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('alumno', 'Alumno'),
        ('docente', 'Docente'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=10, choices=ROLE_CHOICES)
    matricula = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
