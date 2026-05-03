from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from users.permissions import (
    IsAdminOrReadOnly,
    IsDocenteOrAdminOrReadOnly,
)

from .models import (
    CicloEscolar,
    Comentario,
    Entrega,
    Grupo,
    Inscripcion,
    Material,
    Materia,
    Publicacion,
    Tarea,
)
from .serializers import (
    CicloEscolarSerializer,
    ComentarioSerializer,
    EntregaSerializer,
    GrupoSerializer,
    InscripcionSerializer,
    MaterialSerializer,
    MateriaSerializer,
    PublicacionSerializer,
    TareaSerializer,
)


class CicloEscolarViewSet(ModelViewSet):
    queryset = CicloEscolar.objects.all()
    serializer_class = CicloEscolarSerializer
    permission_classes = [IsAdminOrReadOnly]


class MateriaViewSet(ModelViewSet):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer
    permission_classes = [IsAdminOrReadOnly]


class GrupoViewSet(ModelViewSet):
    queryset = Grupo.objects.all()
    serializer_class = GrupoSerializer
    permission_classes = [IsDocenteOrAdminOrReadOnly]

    @action(
        detail=False,
        methods=['post'],
        url_path='join-by-code',
        permission_classes=[IsAuthenticated],
    )
    def join_by_code(self, request):
        """
        Inscripcion por codigo (spec v2.1 seccion 9.1).

        Body: { "codigo": "ABC123" }
        Crea una Inscripcion para el alumno autenticado en el grupo cuyo
        codigo coincida. Falla si el alumno ya esta inscrito en otra clase de
        la misma materia/ciclo (UniqueConstraint del modelo).
        """
        if getattr(request.user, 'rol', None) != 'alumno':
            return Response(
                {'error': 'Solo los alumnos pueden inscribirse por codigo.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        codigo = (request.data.get('codigo') or '').strip().upper()
        if not codigo:
            return Response(
                {'error': 'Debes proporcionar un codigo de grupo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            grupo = Grupo.objects.select_related('materia', 'ciclo').get(codigo=codigo)
        except Grupo.DoesNotExist:
            return Response(
                {'error': 'Codigo de grupo no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = Inscripcion.objects.filter(
            alumno=request.user, grupo=grupo
        ).first()
        if existing:
            return Response(
                {
                    'detail': 'Ya estas inscrito en este grupo.',
                    'inscripcion': InscripcionSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        try:
            inscripcion = Inscripcion.objects.create(
                alumno=request.user,
                grupo=grupo,
                materia=grupo.materia,
                ciclo=grupo.ciclo,
            )
        except IntegrityError:
            return Response(
                {
                    'error': (
                        'Ya estas inscrito en otro grupo de esta materia '
                        'para el ciclo actual.'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                'detail': 'Inscripcion exitosa.',
                'inscripcion': InscripcionSerializer(inscripcion).data,
                'grupo': GrupoSerializer(grupo).data,
            },
            status=status.HTTP_201_CREATED,
        )


class InscripcionViewSet(ModelViewSet):
    queryset = Inscripcion.objects.all()
    serializer_class = InscripcionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Alumno: solo sus inscripciones. Docente: las de sus grupos.
        # Admin: todas.
        user = self.request.user
        rol = getattr(user, 'rol', None)
        if rol == 'alumno':
            return Inscripcion.objects.filter(alumno=user)
        if rol == 'docente':
            return Inscripcion.objects.filter(grupo__docente=user)
        return Inscripcion.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {
                    'error': (
                        'El alumno ya esta inscrito en un grupo de esta '
                        'materia para el ciclo seleccionado.'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )


class TareaViewSet(ModelViewSet):
    queryset = Tarea.objects.all()
    serializer_class = TareaSerializer
    permission_classes = [IsDocenteOrAdminOrReadOnly]

    def get_queryset(self):
        # Alumno: tareas de los grupos en los que esta inscrito.
        # Docente: tareas de los grupos que imparte. Admin: todas.
        user = self.request.user
        rol = getattr(user, 'rol', None)
        if rol == 'alumno':
            grupos_ids = Inscripcion.objects.filter(alumno=user).values_list('grupo_id', flat=True)
            return Tarea.objects.filter(grupo_id__in=grupos_ids)
        if rol == 'docente':
            return Tarea.objects.filter(grupo__docente=user)
        return Tarea.objects.all()


class EntregaViewSet(ModelViewSet):
    queryset = Entrega.objects.all()
    serializer_class = EntregaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Alumno: solo sus propias entregas.
        # Docente: entregas de tareas de sus grupos.
        # Admin: todas.
        user = self.request.user
        rol = getattr(user, 'rol', None)
        if rol == 'alumno':
            return Entrega.objects.filter(alumno=user)
        if rol == 'docente':
            return Entrega.objects.filter(tarea__grupo__docente=user)
        return Entrega.objects.all()

    def perform_create(self, serializer):
        # Si es alumno, forzar alumno=request.user para que no pueda entregar
        # como otro. Admin/docente pueden especificar alumno explicitamente
        # (p.ej. para correcciones manuales).
        rol = getattr(self.request.user, 'rol', None)
        if rol == 'alumno':
            serializer.save(alumno=self.request.user)
        else:
            serializer.save()


class PublicacionViewSet(ModelViewSet):
    queryset = Publicacion.objects.all()
    serializer_class = PublicacionSerializer
    permission_classes = [IsDocenteOrAdminOrReadOnly]

    def get_queryset(self):
        # Alumno: publicaciones de materias en las que esta inscrito.
        # Docente: las que el publico. Admin: todas.
        user = self.request.user
        rol = getattr(user, 'rol', None)
        if rol == 'alumno':
            materias_ids = (
                Inscripcion.objects.filter(alumno=user)
                .values_list('materia_id', flat=True)
                .distinct()
            )
            return Publicacion.objects.filter(materia_id__in=materias_ids)
        if rol == 'docente':
            return Publicacion.objects.filter(autor=user)
        return Publicacion.objects.all()

    def perform_create(self, serializer):
        # El autor siempre es el usuario que publica.
        serializer.save(autor=self.request.user)


class ComentarioViewSet(ModelViewSet):
    queryset = Comentario.objects.all()
    serializer_class = ComentarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtra por publicaciones que el usuario puede ver (mismas reglas que
        # PublicacionViewSet). No bloqueamos por autor del comentario porque
        # cualquier alumno inscrito puede ver los comentarios de sus materias.
        user = self.request.user
        rol = getattr(user, 'rol', None)
        if rol == 'alumno':
            materias_ids = (
                Inscripcion.objects.filter(alumno=user)
                .values_list('materia_id', flat=True)
                .distinct()
            )
            return Comentario.objects.filter(publicacion__materia_id__in=materias_ids)
        if rol == 'docente':
            return Comentario.objects.filter(publicacion__autor=user)
        return Comentario.objects.all()

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)


class MaterialViewSet(ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [IsDocenteOrAdminOrReadOnly]

    def get_queryset(self):
        # Alumno: materiales de sus grupos. Docente: materiales que subio.
        # Admin: todos.
        user = self.request.user
        rol = getattr(user, 'rol', None)
        if rol == 'alumno':
            grupos_ids = Inscripcion.objects.filter(alumno=user).values_list('grupo_id', flat=True)
            return Material.objects.filter(grupo_id__in=grupos_ids)
        if rol == 'docente':
            return Material.objects.filter(autor=user)
        return Material.objects.all()

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
