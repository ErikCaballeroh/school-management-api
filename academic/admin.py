from django.contrib import admin
from .models import (
    CicloEscolar,
    Materia,
    Grupo,
    Inscripcion,
    Tarea,
    Entrega,
    Publicacion,
    Comentario,
    Material,
)

admin.site.register(CicloEscolar)
admin.site.register(Materia)
admin.site.register(Grupo)
admin.site.register(Inscripcion)
admin.site.register(Tarea)
admin.site.register(Entrega)
admin.site.register(Publicacion)
admin.site.register(Comentario)
admin.site.register(Material)
