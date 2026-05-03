"""Backfill de Grupo.codigo + NOT NULL + UNIQUE constraint en Inscripcion."""

from django.db import migrations, models


def backfill_codigos(apps, schema_editor):
    import secrets
    import string

    Grupo = apps.get_model('academic', 'Grupo')
    alphabet = ''.join(
        c for c in (string.ascii_uppercase + string.digits) if c not in 'O0I1'
    )

    def gen():
        return ''.join(secrets.choice(alphabet) for _ in range(6))

    used = set(Grupo.objects.exclude(codigo__isnull=True).values_list('codigo', flat=True))
    used.discard(None)
    used.discard('')

    for grupo in Grupo.objects.filter(models.Q(codigo__isnull=True) | models.Q(codigo='')):
        for _ in range(20):
            candidate = gen()
            if candidate not in used:
                used.add(candidate)
                grupo.codigo = candidate
                grupo.save(update_fields=['codigo'])
                break


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_codigos, noop),
        migrations.AlterField(
            model_name='grupo',
            name='codigo',
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
        migrations.AddConstraint(
            model_name='inscripcion',
            constraint=models.UniqueConstraint(
                fields=('alumno', 'materia', 'ciclo'),
                name='unique_inscripcion_alumno_materia_ciclo',
            ),
        ),
    ]
