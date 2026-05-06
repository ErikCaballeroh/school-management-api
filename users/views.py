from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import User
from .permissions import IsAdminOrReadOnly
from .serializers import UserSerializer


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnly]

    @action(
        detail=False,
        methods=['get'],
        url_path='me',
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        """Devuelve el usuario actualmente autenticado (full profile)."""
        return Response(UserSerializer(request.user).data)

    @action(
        detail=False,
        methods=['post'],
        url_path='change-password',
        permission_classes=[IsAuthenticated],
    )
    def change_password(self, request):
        """
        Cambia la contrasena del usuario autenticado.

        Body: { "actual": "...", "nueva": "..." }
        Verifica la contrasena actual antes de actualizar. Disponible para
        cualquier usuario autenticado (alumno/docente/admin) sobre su propia
        cuenta.
        """
        actual = request.data.get('actual') or ''
        nueva = request.data.get('nueva') or ''
        if not actual or not nueva:
            return Response(
                {'error': 'Debes proporcionar la contrasena actual y la nueva.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(nueva) < 6:
            return Response(
                {'error': 'La nueva contrasena debe tener al menos 6 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(actual):
            return Response(
                {'error': 'La contrasena actual es incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(nueva)
        request.user.save()
        return Response({'detail': 'Contrasena actualizada correctamente.'})
