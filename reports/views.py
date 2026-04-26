import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import django
from django.db import connection
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from academic.models import (
    Grupo,
    Inscripcion,
    Materia,
    Entrega,
    Tarea,
)
from users.models import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CALIFICACION_MINIMA_APROBATORIA = 70


def _close_db_connection(func):
    """Wrapper para cerrar la conexión de BD al terminar el hilo."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            connection.close()
    return wrapper


def _build_pdf(title, subtitle, headers, rows, filename, page_size=letter):
    """Genera un PDF con una tabla profesional y lo retorna como HttpResponse."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=20,
    )

    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(
        Paragraph(
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 12))

    # Construir la tabla
    table_data = [headers] + rows

    table = Table(table_data, repeatRows=1)

    header_bg = colors.HexColor('#16213e')
    row_even = colors.HexColor('#f0f0f5')
    row_odd = colors.white

    style_commands = [
        # Cabecera
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        # Cuerpo
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    # Alternar colores de filas
    for i in range(1, len(table_data)):
        bg = row_even if i % 2 == 0 else row_odd
        style_commands.append(('BACKGROUND', (0, i), (-1, i), bg))

    table.setStyle(TableStyle(style_commands))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# 1. Promedio por Alumno  GET /api/reports/promedio-alumno/<alumno_id>/
#    Calcula el promedio de UN alumno en CADA una de sus materias.
#    Procesamiento paralelo: un hilo por materia.
# ---------------------------------------------------------------------------

@_close_db_connection
def _calcular_promedio_alumno_en_materia(alumno_id, materia):
    """Hilo: calcula el promedio de un alumno en una materia específica."""
    # Obtener todos los grupos de esta materia en los que el alumno está inscrito
    grupos_ids = Inscripcion.objects.filter(
        alumno_id=alumno_id,
        materia=materia,
    ).values_list('grupo_id', flat=True)

    # Obtener las tareas de esos grupos
    tareas_ids = Tarea.objects.filter(
        grupo_id__in=list(grupos_ids)
    ).values_list('id', flat=True)

    # Obtener calificaciones del alumno en esas tareas
    calificaciones = Entrega.objects.filter(
        alumno_id=alumno_id,
        tarea_id__in=list(tareas_ids),
        calificacion__isnull=False,
    ).values_list('calificacion', flat=True)

    calificaciones = list(calificaciones)

    if not calificaciones:
        return {
            'materia': materia.nombre,
            'clave': materia.clave,
            'promedio': 'Sin calificaciones',
            'num_calificaciones': 0,
        }

    promedio = sum(calificaciones) / len(calificaciones)
    return {
        'materia': materia.nombre,
        'clave': materia.clave,
        'promedio': round(float(promedio), 2),
        'num_calificaciones': len(calificaciones),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_promedio_alumno(request, alumno_id):
    """Genera un PDF con el promedio de un alumno en cada una de sus materias."""
    try:
        alumno = User.objects.get(id=alumno_id, rol='alumno')
    except User.DoesNotExist:
        return Response(
            {'error': 'Alumno no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Obtener todas las materias en las que el alumno está inscrito
    materias_ids = Inscripcion.objects.filter(
        alumno=alumno
    ).values_list('materia_id', flat=True).distinct()

    materias = list(Materia.objects.filter(id__in=materias_ids))

    if not materias:
        return Response(
            {'error': 'El alumno no tiene inscripciones.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # --- Procesamiento paralelo: un hilo por materia ---
    resultados = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _calcular_promedio_alumno_en_materia, alumno_id, materia
            ): materia
            for materia in materias
        }
        for future in as_completed(futures):
            resultados.append(future.result())

    # Ordenar por nombre de materia
    resultados.sort(key=lambda r: r['materia'])

    # Calcular promedio general
    promedios_validos = [
        r['promedio'] for r in resultados if isinstance(r['promedio'], (int, float))
    ]
    promedio_general = (
        round(sum(promedios_validos) / len(promedios_validos), 2)
        if promedios_validos
        else 'N/A'
    )

    # Construir filas para el PDF
    headers = ['Materia', 'Clave', 'Calificaciones', 'Promedio']
    rows = [
        [r['materia'], r['clave'], str(r['num_calificaciones']), str(r['promedio'])]
        for r in resultados
    ]
    rows.append(['', '', 'PROMEDIO GENERAL', str(promedio_general)])

    nombre_alumno = alumno.nombre or alumno.email
    return _build_pdf(
        title=f'Promedio por Alumno',
        subtitle=f'Alumno: {nombre_alumno}  |  Matrícula: {alumno.matricula or "N/A"}',
        headers=headers,
        rows=rows,
        filename=f'promedio_alumno_{alumno_id}.pdf',
    )


# ---------------------------------------------------------------------------
# 2. Promedio por Grupo  GET /api/reports/promedio-grupo/<grupo_id>/
#    Calificaciones y promedio de cada alumno dentro de UN grupo.
#    Procesamiento paralelo: un hilo por alumno.
# ---------------------------------------------------------------------------

@_close_db_connection
def _calcular_promedio_alumno_en_grupo(alumno, grupo):
    """Hilo: calcula el promedio de un alumno dentro de un grupo."""
    tareas_ids = Tarea.objects.filter(
        grupo=grupo
    ).values_list('id', flat=True)

    calificaciones = Entrega.objects.filter(
        alumno=alumno,
        tarea_id__in=list(tareas_ids),
        calificacion__isnull=False,
    ).values_list('calificacion', flat=True)

    calificaciones = list(calificaciones)

    if not calificaciones:
        return {
            'alumno_nombre': alumno.nombre or alumno.email,
            'matricula': alumno.matricula or 'N/A',
            'promedio': 'Sin calificaciones',
            'num_calificaciones': 0,
        }

    promedio = sum(calificaciones) / len(calificaciones)
    return {
        'alumno_nombre': alumno.nombre or alumno.email,
        'matricula': alumno.matricula or 'N/A',
        'promedio': round(float(promedio), 2),
        'num_calificaciones': len(calificaciones),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_promedio_grupo(request, grupo_id):
    """Genera un PDF con el promedio de cada alumno de un grupo."""
    try:
        grupo = Grupo.objects.select_related('materia', 'docente').get(id=grupo_id)
    except Grupo.DoesNotExist:
        return Response(
            {'error': 'Grupo no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Obtener alumnos inscritos en el grupo
    alumnos_ids = Inscripcion.objects.filter(
        grupo=grupo
    ).values_list('alumno_id', flat=True).distinct()

    alumnos = list(User.objects.filter(id__in=alumnos_ids))

    if not alumnos:
        return Response(
            {'error': 'El grupo no tiene alumnos inscritos.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # --- Procesamiento paralelo: un hilo por alumno ---
    resultados = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _calcular_promedio_alumno_en_grupo, alumno, grupo
            ): alumno
            for alumno in alumnos
        }
        for future in as_completed(futures):
            resultados.append(future.result())

    # Ordenar por nombre
    resultados.sort(key=lambda r: r['alumno_nombre'])

    # Promedio general del grupo
    promedios_validos = [
        r['promedio'] for r in resultados if isinstance(r['promedio'], (int, float))
    ]
    promedio_grupo = (
        round(sum(promedios_validos) / len(promedios_validos), 2)
        if promedios_validos
        else 'N/A'
    )

    headers = ['Matrícula', 'Alumno', 'Calificaciones', 'Promedio']
    rows = [
        [str(r['matricula']), r['alumno_nombre'], str(r['num_calificaciones']), str(r['promedio'])]
        for r in resultados
    ]
    rows.append(['', '', 'PROMEDIO DEL GRUPO', str(promedio_grupo)])

    docente_nombre = grupo.docente.nombre or grupo.docente.email
    return _build_pdf(
        title='Promedio por Grupo',
        subtitle=(
            f'Grupo: {grupo.nombre}  |  Materia: {grupo.materia.nombre}  |  '
            f'Docente: {docente_nombre}'
        ),
        headers=headers,
        rows=rows,
        filename=f'promedio_grupo_{grupo_id}.pdf',
    )


# ---------------------------------------------------------------------------
# 3. Promedio por Materia  GET /api/reports/promedio-materia/<materia_id>/
#    Promedio de todos los alumnos de todos los grupos de UNA materia.
#    Procesamiento paralelo: un hilo por grupo de la materia.
# ---------------------------------------------------------------------------

@_close_db_connection
def _calcular_promedio_grupo_en_materia(grupo):
    """Hilo: calcula las calificaciones de todos los alumnos de un grupo."""
    alumnos_ids = Inscripcion.objects.filter(
        grupo=grupo
    ).values_list('alumno_id', flat=True).distinct()

    alumnos = list(User.objects.filter(id__in=alumnos_ids))

    tareas_ids = list(
        Tarea.objects.filter(grupo=grupo).values_list('id', flat=True)
    )

    resultados_alumnos = []
    for alumno in alumnos:
        calificaciones = list(
            Entrega.objects.filter(
                alumno=alumno,
                tarea_id__in=tareas_ids,
                calificacion__isnull=False,
            ).values_list('calificacion', flat=True)
        )
        promedio = (
            round(float(sum(calificaciones) / len(calificaciones)), 2)
            if calificaciones
            else 'Sin calificaciones'
        )
        resultados_alumnos.append({
            'alumno_nombre': alumno.nombre or alumno.email,
            'matricula': alumno.matricula or 'N/A',
            'grupo_nombre': grupo.nombre,
            'promedio': promedio,
        })

    return resultados_alumnos


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_promedio_materia(request, materia_id):
    """Genera un PDF con el promedio de todos los alumnos en todos los grupos de una materia."""
    try:
        materia = Materia.objects.get(id=materia_id)
    except Materia.DoesNotExist:
        return Response(
            {'error': 'Materia no encontrada.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    grupos = list(Grupo.objects.filter(materia=materia))

    if not grupos:
        return Response(
            {'error': 'La materia no tiene grupos asignados.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # --- Procesamiento paralelo: un hilo por grupo ---
    todos_resultados = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(_calcular_promedio_grupo_en_materia, grupo): grupo
            for grupo in grupos
        }
        for future in as_completed(futures):
            todos_resultados.extend(future.result())

    # Ordenar por grupo y luego por alumno
    todos_resultados.sort(key=lambda r: (r['grupo_nombre'], r['alumno_nombre']))

    # Promedio general de la materia
    promedios_validos = [
        r['promedio'] for r in todos_resultados
        if isinstance(r['promedio'], (int, float))
    ]
    promedio_materia = (
        round(sum(promedios_validos) / len(promedios_validos), 2)
        if promedios_validos
        else 'N/A'
    )

    headers = ['Grupo', 'Matrícula', 'Alumno', 'Promedio']
    rows = [
        [r['grupo_nombre'], str(r['matricula']), r['alumno_nombre'], str(r['promedio'])]
        for r in todos_resultados
    ]
    rows.append(['', '', 'PROMEDIO DE LA MATERIA', str(promedio_materia)])

    return _build_pdf(
        title='Promedio por Materia',
        subtitle=f'Materia: {materia.nombre}  |  Clave: {materia.clave}',
        headers=headers,
        rows=rows,
        filename=f'promedio_materia_{materia_id}.pdf',
        page_size=landscape(letter),
    )


# ---------------------------------------------------------------------------
# 4. Índice de Reprobación  GET /api/reports/indice-reprobacion/<grupo_id>/
#    Porcentaje de aprobación/reprobación de UN grupo.
#    Procesamiento paralelo: un hilo por alumno.
# ---------------------------------------------------------------------------

@_close_db_connection
def _evaluar_aprobacion_alumno(alumno, grupo):
    """Hilo: determina si un alumno aprueba o reprueba en un grupo."""
    tareas_ids = list(
        Tarea.objects.filter(grupo=grupo).values_list('id', flat=True)
    )

    calificaciones = list(
        Entrega.objects.filter(
            alumno=alumno,
            tarea_id__in=tareas_ids,
            calificacion__isnull=False,
        ).values_list('calificacion', flat=True)
    )

    if not calificaciones:
        promedio = 0
        estatus = 'Sin calificaciones'
    else:
        promedio = round(float(sum(calificaciones) / len(calificaciones)), 2)
        estatus = 'Aprobado' if promedio >= CALIFICACION_MINIMA_APROBATORIA else 'Reprobado'

    return {
        'alumno_nombre': alumno.nombre or alumno.email,
        'matricula': alumno.matricula or 'N/A',
        'promedio': promedio,
        'estatus': estatus,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_indice_reprobacion(request, grupo_id):
    """Genera un PDF con el índice de reprobación de un grupo."""
    try:
        grupo = Grupo.objects.select_related('materia', 'docente').get(id=grupo_id)
    except Grupo.DoesNotExist:
        return Response(
            {'error': 'Grupo no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    alumnos_ids = Inscripcion.objects.filter(
        grupo=grupo
    ).values_list('alumno_id', flat=True).distinct()

    alumnos = list(User.objects.filter(id__in=alumnos_ids))

    if not alumnos:
        return Response(
            {'error': 'El grupo no tiene alumnos inscritos.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # --- Procesamiento paralelo: un hilo por alumno ---
    resultados = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(_evaluar_aprobacion_alumno, alumno, grupo): alumno
            for alumno in alumnos
        }
        for future in as_completed(futures):
            resultados.append(future.result())

    resultados.sort(key=lambda r: r['alumno_nombre'])

    # Calcular estadísticas
    total = len(resultados)
    aprobados = sum(1 for r in resultados if r['estatus'] == 'Aprobado')
    reprobados = sum(1 for r in resultados if r['estatus'] == 'Reprobado')
    sin_calif = sum(1 for r in resultados if r['estatus'] == 'Sin calificaciones')

    pct_aprobados = round((aprobados / total) * 100, 2) if total else 0
    pct_reprobados = round((reprobados / total) * 100, 2) if total else 0

    headers = ['Matrícula', 'Alumno', 'Promedio', 'Estatus']
    rows = [
        [str(r['matricula']), r['alumno_nombre'], str(r['promedio']), r['estatus']]
        for r in resultados
    ]
    rows.append(['', '', '', ''])
    rows.append(['', 'TOTAL ALUMNOS', str(total), ''])
    rows.append(['', 'APROBADOS', str(aprobados), f'{pct_aprobados}%'])
    rows.append(['', 'REPROBADOS', str(reprobados), f'{pct_reprobados}%'])
    rows.append(['', 'SIN CALIFICACIONES', str(sin_calif), ''])

    docente_nombre = grupo.docente.nombre or grupo.docente.email
    return _build_pdf(
        title='Índice de Reprobación',
        subtitle=(
            f'Grupo: {grupo.nombre}  |  Materia: {grupo.materia.nombre}  |  '
            f'Docente: {docente_nombre}  |  '
            f'Calificación mínima aprobatoria: {CALIFICACION_MINIMA_APROBATORIA}'
        ),
        headers=headers,
        rows=rows,
        filename=f'indice_reprobacion_{grupo_id}.pdf',
    )
