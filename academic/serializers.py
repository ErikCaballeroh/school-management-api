from rest_framework import serializers
from .models import (
    Materia,
    CicloEscolar,
    Grupo,
    Inscripcion,
    Tarea,
    Entrega,
    Publicacion,
    Comentario,
)


class CicloEscolarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloEscolar
        fields = '__all__'


class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = '__all__'


class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = '__all__'


class InscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inscripcion
        fields = '__all__'


class NullableDateTimeField(serializers.DateTimeField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('style', {'input_type': 'text'})
        super().__init__(*args, **kwargs)

    def to_internal_value(self, value):
        if value == '' or value is None:
            return None
        return super().to_internal_value(value)


class TareaSerializer(serializers.ModelSerializer):
    fecha_limite = NullableDateTimeField(required=False, allow_null=True, default=None)

    class Meta:
        model = Tarea
        fields = '__all__'


class EntregaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entrega
        fields = '__all__'


class PublicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publicacion
        fields = '__all__'


class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = '__all__'
