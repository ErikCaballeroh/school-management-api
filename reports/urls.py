from django.urls import path

from .json_views import (
    indice_reprobacion_json,
    promedio_alumno_json,
    promedio_grupo_json,
    promedio_materia_json,
)
from .views import (
    reporte_indice_reprobacion,
    reporte_promedio_alumno,
    reporte_promedio_grupo,
    reporte_promedio_materia,
)

urlpatterns = [
    # PDFs
    path('promedio-alumno/<int:alumno_id>/', reporte_promedio_alumno, name='reporte-promedio-alumno'),
    path('promedio-grupo/<int:grupo_id>/', reporte_promedio_grupo, name='reporte-promedio-grupo'),
    path('promedio-materia/<int:materia_id>/', reporte_promedio_materia, name='reporte-promedio-materia'),
    path('indice-reprobacion/<int:grupo_id>/', reporte_indice_reprobacion, name='reporte-indice-reprobacion'),

    # JSON (con cache + medicion de paralelismo)
    path('json/promedio-alumno/<int:alumno_id>/', promedio_alumno_json, name='json-promedio-alumno'),
    path('json/promedio-grupo/<int:grupo_id>/', promedio_grupo_json, name='json-promedio-grupo'),
    path('json/promedio-materia/<int:materia_id>/', promedio_materia_json, name='json-promedio-materia'),
    path('json/indice-reprobacion/<int:grupo_id>/', indice_reprobacion_json, name='json-indice-reprobacion'),
]
