from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('alumno', 'Alumno'),
        ('docente', 'Docente'),
        ('admin', 'Admin'),
    )

    rol = models.CharField(max_length=10, choices=ROLE_CHOICES)
    matricula = models.CharField(max_length=50, null=True, blank=True)
    activo = models.BooleanField(default=True)
