"""
Endpoints JSON de reportes (consumidos por el dashboard React).

A diferencia de los reportes PDF, estos:
  - Devuelven JSON cacheado (TTL 60s) para no recomputar bajo carga.
  - Usan procesamiento paralelo (hilos por defecto, procesos opcional via
    ?mode=process) para demostrar escalabilidad por nucleos.

La logica de calculo se reusa de reports.views para no duplicar.
"""

import time

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academic.models import Grupo, Inscripcion, Materia, Tarea
from system.parallel import cached_report, run_parallel
from users.models import User

from .views import (
    CALIFICACION_MINIMA_APROBATORIA,
    _calcular_promedio_alumno_en_grupo,
    _calcular_promedio_alumno_en_materia,
    _calcular_promedio_grupo_en_materia,
    _evaluar_aprobacion_alumno,
)


def _exec_mode(request):
    return 'process' if request.GET.get('mode') == 'process' else 'thread'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def promedio_alumno_json(request, alumno_id):
    mode = _exec_mode(request)

    @cached_report(f'promedio_alumno:{mode}', ttl_seconds=60)
    def _build(alumno_id):
        try:
            alumno = User.objects.get(id=alumno_id, rol='alumno')
        except User.DoesNotExist:
            return {'error': 'Alumno no encontrado.'}

        materias_ids = (
            Inscripcion.objects.filter(alumno=alumno)
            .values_list('materia_id', flat=True)
            .distinct()
        )
        materias = list(Materia.objects.filter(id__in=materias_ids))
        if not materias:
            return {'error': 'El alumno no tiene inscripciones.'}

        started = time.perf_counter()
        resultados = run_parallel(
            lambda m: _calcular_promedio_alumno_en_materia(alumno_id, m),
            materias,
            mode='thread',  # el ORM se rompe con processes aqui
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        promedios = [r['promedio'] for r in resultados if isinstance(r['promedio'], (int, float))]
        promedio_general = round(sum(promedios) / len(promedios), 2) if promedios else None

        return {
            'alumno': {'id': alumno.id, 'nombre': alumno.nombre, 'matricula': alumno.matricula},
            'materias': sorted(resultados, key=lambda r: r['materia']),
            'promedio_general': promedio_general,
            'parallel': {
                'mode': mode,
                'tasks': len(materias),
                'elapsed_ms': elapsed_ms,
            },
        }

    return Response(_build(alumno_id))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def promedio_grupo_json(request, grupo_id):
    mode = _exec_mode(request)

    @cached_report(f'promedio_grupo:{mode}', ttl_seconds=60)
    def _build(grupo_id):
        try:
            grupo = Grupo.objects.select_related('materia', 'docente').get(id=grupo_id)
        except Grupo.DoesNotExist:
            return {'error': 'Grupo no encontrado.'}

        alumnos_ids = (
            Inscripcion.objects.filter(grupo=grupo)
            .values_list('alumno_id', flat=True)
            .distinct()
        )
        alumnos = list(User.objects.filter(id__in=alumnos_ids))
        if not alumnos:
            return {'error': 'El grupo no tiene alumnos inscritos.'}

        started = time.perf_counter()
        resultados = run_parallel(
            lambda a: _calcular_promedio_alumno_en_grupo(a, grupo),
            alumnos,
            mode='thread',
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        promedios = [r['promedio'] for r in resultados if isinstance(r['promedio'], (int, float))]
        promedio_grupo = round(sum(promedios) / len(promedios), 2) if promedios else None

        return {
            'grupo': {
                'id': grupo.id,
                'nombre': grupo.nombre,
                'materia': grupo.materia.nombre,
                'docente': grupo.docente.nombre,
            },
            'alumnos': sorted(resultados, key=lambda r: r['alumno_nombre']),
            'promedio_grupo': promedio_grupo,
            'parallel': {
                'mode': mode,
                'tasks': len(alumnos),
                'elapsed_ms': elapsed_ms,
            },
        }

    return Response(_build(grupo_id))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def promedio_materia_json(request, materia_id):
    mode = _exec_mode(request)

    @cached_report(f'promedio_materia:{mode}', ttl_seconds=60)
    def _build(materia_id):
        try:
            materia = Materia.objects.get(id=materia_id)
        except Materia.DoesNotExist:
            return {'error': 'Materia no encontrada.'}

        grupos = list(Grupo.objects.filter(materia=materia))
        if not grupos:
            return {'error': 'La materia no tiene grupos asignados.'}

        started = time.perf_counter()
        nested = run_parallel(_calcular_promedio_grupo_en_materia, grupos, mode='thread')
        resultados = [item for sub in nested for item in sub]
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        promedios = [r['promedio'] for r in resultados if isinstance(r['promedio'], (int, float))]
        promedio_materia = round(sum(promedios) / len(promedios), 2) if promedios else None

        return {
            'materia': {'id': materia.id, 'nombre': materia.nombre, 'clave': materia.clave},
            'alumnos': sorted(resultados, key=lambda r: (r['grupo_nombre'], r['alumno_nombre'])),
            'promedio_materia': promedio_materia,
            'parallel': {
                'mode': mode,
                'tasks': len(grupos),
                'elapsed_ms': elapsed_ms,
            },
        }

    return Response(_build(materia_id))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def indice_reprobacion_json(request, grupo_id):
    mode = _exec_mode(request)

    @cached_report(f'indice_reprobacion:{mode}', ttl_seconds=60)
    def _build(grupo_id):
        try:
            grupo = Grupo.objects.select_related('materia', 'docente').get(id=grupo_id)
        except Grupo.DoesNotExist:
            return {'error': 'Grupo no encontrado.'}

        alumnos_ids = (
            Inscripcion.objects.filter(grupo=grupo)
            .values_list('alumno_id', flat=True)
            .distinct()
        )
        alumnos = list(User.objects.filter(id__in=alumnos_ids))
        if not alumnos:
            return {'error': 'El grupo no tiene alumnos inscritos.'}

        started = time.perf_counter()
        resultados = run_parallel(
            lambda a: _evaluar_aprobacion_alumno(a, grupo),
            alumnos,
            mode='thread',
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        total = len(resultados)
        aprobados = sum(1 for r in resultados if r['estatus'] == 'Aprobado')
        reprobados = sum(1 for r in resultados if r['estatus'] == 'Reprobado')
        sin_calif = sum(1 for r in resultados if r['estatus'] == 'Sin calificaciones')

        return {
            'grupo': {
                'id': grupo.id,
                'nombre': grupo.nombre,
                'materia': grupo.materia.nombre,
            },
            'minimo_aprobatorio': CALIFICACION_MINIMA_APROBATORIA,
            'alumnos': sorted(resultados, key=lambda r: r['alumno_nombre']),
            'totales': {
                'total': total,
                'aprobados': aprobados,
                'reprobados': reprobados,
                'sin_calificaciones': sin_calif,
                'pct_aprobados': round((aprobados / total) * 100, 2) if total else 0,
                'pct_reprobados': round((reprobados / total) * 100, 2) if total else 0,
            },
            'parallel': {
                'mode': mode,
                'tasks': len(alumnos),
                'elapsed_ms': elapsed_ms,
            },
        }

    return Response(_build(grupo_id))
