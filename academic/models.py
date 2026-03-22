from django.conf import settings
from django.db import models


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
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.CASCADE)


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
    archivo_nombre = models.CharField(max_length=50)
    tamano_bytes = models.IntegerField()
    calificacion = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    comentario = models.TextField(max_length=1000)
    fecha_entrega = models.DateTimeField(null=True, blank=True)


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
