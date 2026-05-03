"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from academic.views import (
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
from users.views import UserViewSet

# Router único que muestra todo en la raíz /api/
router = DefaultRouter()

# Academic
router.register(r'ciclos', CicloEscolarViewSet)
router.register(r'materias', MateriaViewSet)
router.register(r'grupos', GrupoViewSet)
router.register(r'inscripciones', InscripcionViewSet)
router.register(r'tareas', TareaViewSet)
router.register(r'entregas', EntregaViewSet)
router.register(r'publicaciones', PublicacionViewSet)
router.register(r'comentarios', ComentarioViewSet)
router.register(r'materiales', MaterialViewSet)

# Users
router.register(r'users', UserViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),

    # Todas las rutas del router unificado
    path('api/', include(router.urls)),

    # Rutas manuales (upload y reports)
    path('api/upload/', __import__('academic.upload_view', fromlist=['FileUploadView']).FileUploadView.as_view(), name='file-upload'),
    path('api/reports/', include('reports.urls')),

    # Monitoreo del sistema (PIA)
    path('api/system/', include('system.urls')),

    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
