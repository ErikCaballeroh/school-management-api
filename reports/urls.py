from django.urls import path
from .views import (
    reporte_promedio_alumno,
    reporte_promedio_grupo,
    reporte_promedio_materia,
    reporte_indice_reprobacion,
)

urlpatterns = [
    path(
        'promedio-alumno/<int:alumno_id>/',
        reporte_promedio_alumno,
        name='reporte-promedio-alumno',
    ),
    path(
        'promedio-grupo/<int:grupo_id>/',
        reporte_promedio_grupo,
        name='reporte-promedio-grupo',
    ),
    path(
        'promedio-materia/<int:materia_id>/',
        reporte_promedio_materia,
        name='reporte-promedio-materia',
    ),
    path(
        'indice-reprobacion/<int:grupo_id>/',
        reporte_indice_reprobacion,
        name='reporte-indice-reprobacion',
    ),
]
