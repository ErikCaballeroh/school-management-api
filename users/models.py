from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('alumno', 'Alumno'),
        ('docente', 'Docente'),
        ('admin', 'Admin'),
    )

    nombre = models.CharField(max_length=150, blank=True, default='')
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=10, choices=ROLE_CHOICES)
    matricula = models.IntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        self.is_active = self.activo
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
