from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'nombre', 'rol',
            'matricula', 'activo', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
