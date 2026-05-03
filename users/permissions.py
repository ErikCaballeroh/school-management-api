"""
Permisos por rol (alumno / docente / admin).

Se aplican a nivel de ViewSet. La logica es deliberadamente simple para no
romper la API existente: admins pueden todo; en endpoints de escritura el rol
exacto se exige cuando aplica.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


def _rol(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None
    # Un superuser de Django siempre cuenta como admin (cubre el caso de
    # `manage.py createsuperuser` que no setea el campo `rol`).
    if getattr(user, 'is_superuser', False):
        return 'admin'
    return getattr(user, 'rol', None)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return _rol(request) == 'admin'


class IsDocente(BasePermission):
    def has_permission(self, request, view):
        return _rol(request) == 'docente'


class IsAlumno(BasePermission):
    def has_permission(self, request, view):
        return _rol(request) == 'alumno'


class IsAdminOrReadOnly(BasePermission):
    """Cualquier autenticado puede leer; solo admin puede escribir."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _rol(request) == 'admin'


class IsDocenteOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return _rol(request) in ('docente', 'admin')


class IsDocenteOrAdminOrReadOnly(BasePermission):
    """Lectura para cualquier autenticado; escritura solo docente o admin."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _rol(request) in ('docente', 'admin')
