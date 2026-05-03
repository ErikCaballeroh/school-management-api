from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    # Aceptamos password en create (write-only). Si no se manda en update no
    # se cambia.
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # AbstractUser exige username; lo aceptamos opcional y si no llega lo
    # generamos a partir del email para no romper el flujo del frontend.
    username = serializers.CharField(required=False, allow_blank=True)
    # Aceptamos cualquier string en `rol` y lo normalizamos a lowercase en
    # validate_rol (acepta 'Alumno', 'ALUMNO', etc.).
    rol = serializers.CharField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'nombre', 'rol',
            'matricula', 'activo', 'created_at', 'password',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_rol(self, value):
        # Acepta variantes con mayuscula del frontend.
        normalized = (value or '').lower()
        valid = {choice[0] for choice in User.ROLE_CHOICES}
        if normalized not in valid:
            raise serializers.ValidationError(
                f'Rol invalido. Debe ser uno de: {", ".join(sorted(valid))}.'
            )
        return normalized

    def validate(self, attrs):
        # Si no llega username, lo derivamos del email (parte antes de @).
        if not attrs.get('username'):
            email = attrs.get('email') or (self.instance.email if self.instance else '')
            if email:
                attrs['username'] = email.split('@')[0]
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
