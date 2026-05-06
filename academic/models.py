import secrets
import string

from django.conf import settings
from django.db import models


def _generate_codigo(length=6):
    """Codigo de inscripcion legible (sin caracteres ambiguos: O/0, I/1)."""
    alphabet = ''.join(c for c in (string.ascii_uppercase + string.digits) if c not in 'O0I1')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class CicloEscolar(models.Model):
    nombre = models.CharField(max_length=50)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField()

    def __str__(self):
        return self.nombre


class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    clave = models.CharField(max_length=50)
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre


class Grupo(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50, unique=True, blank=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # Genera un codigo unico si no se proporciono uno (spec: codigo NOT
        # NULL, usado en el flujo de join-by-code del alumno).
        if not self.codigo:
            for _ in range(10):
                candidate = _generate_codigo()
                if not Grupo.objects.filter(codigo=candidate).exists():
                    self.codigo = candidate
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'


class Inscripcion(models.Model):
    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    ciclo = models.ForeignKey(
        CicloEscolar,
        on_delete=models.CASCADE
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Spec v2.1 6.5: un alumno no puede estar en dos grupos de la misma
        # materia en el mismo ciclo.
        constraints = [
            models.UniqueConstraint(
                fields=['alumno', 'materia', 'ciclo'],
                name='unique_inscripcion_alumno_materia_ciclo',
            ),
        ]


class Tarea(models.Model):
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField(max_length=1000)
    fecha_limite = models.DateTimeField(null=True, blank=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class Entrega(models.Model):
    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE)
    archivo_url = models.CharField(max_length=200)
    video_url = models.CharField(max_length=200, blank=True, default='')
    nombre_archivo = models.CharField(max_length=50)
    tamano_bytes = models.IntegerField()
    calificacion = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    comentario = models.TextField(max_length=1000, blank=True, default='')
    fecha_entrega = models.DateTimeField(auto_now_add=True)


class Publicacion(models.Model):
    titulo = models.CharField(max_length=100)
    contenido = models.TextField(max_length=2000)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Comentario(models.Model):
    contenido = models.TextField(max_length=1000)
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Material(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=10, default='archivo')
    archivo_url = models.CharField(max_length=200, blank=True, default='')
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
