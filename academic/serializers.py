from rest_framework import serializers

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


class CicloEscolarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CicloEscolar
        fields = '__all__'


class MateriaSerializer(serializers.ModelSerializer):
    ciclo_nombre = serializers.CharField(source='ciclo.nombre', read_only=True)

    class Meta:
        model = Materia
        fields = ['id', 'nombre', 'clave', 'ciclo', 'ciclo_nombre']


class GrupoSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    clave = serializers.CharField(source='materia.clave', read_only=True)
    docente_nombre = serializers.CharField(source='docente.nombre', read_only=True)
    ciclo_nombre = serializers.CharField(source='ciclo.nombre', read_only=True)
    cicloId = serializers.IntegerField(source='ciclo_id', read_only=True)
    alumnos = serializers.SerializerMethodField()

    class Meta:
        model = Grupo
        fields = [
            'id', 'nombre', 'codigo',
            'materia', 'materia_nombre', 'clave',
            'docente', 'docente_nombre',
            'ciclo', 'ciclo_nombre', 'cicloId',
            'alumnos',
        ]
        read_only_fields = ['codigo']  # se autogenera

    def get_alumnos(self, obj):
        return list(
            Inscripcion.objects.filter(grupo=obj).values_list('alumno_id', flat=True)
        )


class InscripcionSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.CharField(source='alumno.nombre', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)

    class Meta:
        model = Inscripcion
        fields = [
            'id', 'alumno', 'alumno_nombre',
            'grupo', 'materia', 'materia_nombre', 'ciclo',
            'fecha_inscripcion',
        ]


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
    grupo_nombre = serializers.CharField(source='grupo.nombre', read_only=True)
    materia_nombre = serializers.CharField(source='grupo.materia.nombre', read_only=True)
    docente_nombre = serializers.CharField(source='grupo.docente.nombre', read_only=True)

    class Meta:
        model = Tarea
        fields = [
            'id', 'titulo', 'descripcion', 'fecha_limite',
            'grupo', 'grupo_nombre', 'materia_nombre', 'docente_nombre',
            'created_at',
        ]


class EntregaSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.CharField(source='alumno.nombre', read_only=True)
    tarea_titulo = serializers.CharField(source='tarea.titulo', read_only=True)

    class Meta:
        model = Entrega
        fields = [
            'id', 'alumno', 'alumno_nombre', 'tarea', 'tarea_titulo',
            'archivo_url', 'video_url', 'nombre_archivo', 'tamano_bytes',
            'calificacion', 'comentario', 'fecha_entrega',
        ]
        # alumno se asigna automaticamente en perform_create cuando el rol es alumno
        extra_kwargs = {
            'alumno': {'required': False},
            'comentario': {'required': False, 'allow_blank': True, 'default': ''},
            'archivo_url': {'required': False, 'allow_blank': True, 'default': ''},
            'video_url': {'required': False, 'allow_blank': True, 'default': ''},
            'nombre_archivo': {'required': False, 'allow_blank': True, 'default': ''},
            'tamano_bytes': {'required': False, 'default': 0},
        }


class PublicacionSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    # Acepta `grupo` desde el frontend para derivar la materia. El frontend
    # publica desde un grupo y el backend asocia automaticamente con la materia
    # de ese grupo (RF-08: el canal vive a nivel de materia).
    grupo = serializers.IntegerField(write_only=True, required=False)
    # Acepta `texto` como alias del campo del frontend.
    texto = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Publicacion
        fields = [
            'id', 'titulo', 'contenido', 'texto',
            'materia', 'materia_nombre',
            'grupo',
            'autor', 'autor_nombre', 'created_at',
        ]
        extra_kwargs = {
            'autor': {'required': False},  # se auto-asigna
            'materia': {'required': False},  # se deriva del grupo si llega
            'contenido': {'required': False, 'allow_blank': True, 'default': ''},
        }

    def validate(self, attrs):
        grupo_id = attrs.pop('grupo', None)
        if not attrs.get('materia') and grupo_id:
            try:
                grupo = Grupo.objects.get(id=grupo_id)
            except Grupo.DoesNotExist:
                raise serializers.ValidationError({'grupo': 'Grupo no encontrado.'})
            attrs['materia'] = grupo.materia

        # `texto` es alias de contenido (aceptamos ambos)
        texto = attrs.pop('texto', None)
        if texto and not attrs.get('contenido'):
            attrs['contenido'] = texto

        if not attrs.get('contenido'):
            raise serializers.ValidationError({'contenido': 'El contenido es requerido.'})
        if not attrs.get('materia'):
            raise serializers.ValidationError({'materia': 'Debe especificar materia o grupo.'})
        return attrs


class ComentarioSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre', read_only=True)
    # Alias `texto` desde el frontend.
    texto = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Comentario
        fields = [
            'id', 'contenido', 'texto',
            'publicacion', 'autor', 'autor_nombre', 'created_at',
        ]
        extra_kwargs = {
            'autor': {'required': False},  # se auto-asigna
            'contenido': {'required': False, 'allow_blank': True, 'default': ''},
        }

    def validate(self, attrs):
        texto = attrs.pop('texto', None)
        if texto and not attrs.get('contenido'):
            attrs['contenido'] = texto
        if not attrs.get('contenido'):
            raise serializers.ValidationError({'contenido': 'El contenido es requerido.'})
        return attrs


class MaterialSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source='autor.nombre', read_only=True)

    class Meta:
        model = Material
        fields = [
            'id', 'titulo', 'descripcion', 'tipo', 'archivo_url',
            'grupo', 'autor', 'autor_nombre', 'created_at',
        ]
        extra_kwargs = {
            'autor': {'required': False},  # se auto-asigna
            'descripcion': {'required': False, 'allow_blank': True, 'default': ''},
            'archivo_url': {'required': False, 'allow_blank': True, 'default': ''},
        }
