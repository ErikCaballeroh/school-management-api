from rest_framework.viewsets import ModelViewSet
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
from .serializers import (
    CicloEscolarSerializer,
    MateriaSerializer,
    GrupoSerializer,
    InscripcionSerializer,
    TareaSerializer,
    EntregaSerializer,
    PublicacionSerializer,
    ComentarioSerializer,
    MaterialSerializer,
)


class CicloEscolarViewSet(ModelViewSet):
    queryset = CicloEscolar.objects.all()
    serializer_class = CicloEscolarSerializer


class MateriaViewSet(ModelViewSet):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer


class GrupoViewSet(ModelViewSet):
    queryset = Grupo.objects.all()
    serializer_class = GrupoSerializer


class InscripcionViewSet(ModelViewSet):
    queryset = Inscripcion.objects.all()
    serializer_class = InscripcionSerializer


class TareaViewSet(ModelViewSet):
    queryset = Tarea.objects.all()
    serializer_class = TareaSerializer


class EntregaViewSet(ModelViewSet):
    queryset = Entrega.objects.all()
    serializer_class = EntregaSerializer


class PublicacionViewSet(ModelViewSet):
    queryset = Publicacion.objects.all()
    serializer_class = PublicacionSerializer


class ComentarioViewSet(ModelViewSet):
    queryset = Comentario.objects.all()
    serializer_class = ComentarioSerializer


class MaterialViewSet(ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
