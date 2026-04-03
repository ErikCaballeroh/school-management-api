from rest_framework.routers import DefaultRouter
from .views import (
    CicloEscolarViewSet,
    MateriaViewSet,
    GrupoViewSet,
    InscripcionViewSet,
    TareaViewSet,
    EntregaViewSet,
    PublicacionViewSet,
    ComentarioViewSet,
    MaterialViewSet,
)

router = DefaultRouter()
router.register(r'ciclos', CicloEscolarViewSet)
router.register(r'materias', MateriaViewSet)
router.register(r'grupos', GrupoViewSet)
router.register(r'inscripciones', InscripcionViewSet)
router.register(r'tareas', TareaViewSet)
router.register(r'entregas', EntregaViewSet)
router.register(r'publicaciones', PublicacionViewSet)
router.register(r'comentarios', ComentarioViewSet)
router.register(r'materiales', MaterialViewSet)

urlpatterns = router.urls
