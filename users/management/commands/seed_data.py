import random
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from academic.models import CicloEscolar, Grupo, Inscripcion, Materia
from users.models import User


class Command(BaseCommand):
    help = "Genera datos iniciales para desarrollo y pruebas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--students",
            type=int,
            default=100,
            help="Cantidad de alumnos a crear (default: 100)",
        )
        parser.add_argument(
            "--teachers",
            type=int,
            default=8,
            help="Cantidad de docentes a crear (default: 8)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        student_count = max(1, options["students"])
        teacher_count = max(1, options["teachers"])

        ciclo = self._get_or_create_ciclo_activo()
        teachers_created = self._create_teachers(teacher_count)
        materias_created = self._create_materias_y_grupos(ciclo)
        students_created, enrollments_created = self._create_students_and_enrollments(
            student_count,
            ciclo,
        )

        self.stdout.write(self.style.SUCCESS("Seed completada correctamente."))
        self.stdout.write(
            (
                f"Ciclo activo: {ciclo.nombre} | "
                f"Docentes creados: {teachers_created} | "
                f"Materias nuevas: {materias_created} | "
                f"Alumnos creados: {students_created} | "
                f"Inscripciones nuevas: {enrollments_created}"
            )
        )

    def _get_or_create_ciclo_activo(self):
        ciclo_activo = CicloEscolar.objects.filter(activo=True).first()
        if ciclo_activo:
            return ciclo_activo

        today = date.today()
        ciclo, _ = CicloEscolar.objects.get_or_create(
            nombre=f"{today.year}-{today.year + 1}",
            defaults={
                "fecha_inicio": date(today.year, 8, 1),
                "fecha_fin": date(today.year + 1, 7, 31),
                "activo": True,
            },
        )
        return ciclo

    def _create_teachers(self, count):
        created = 0
        for i in range(1, count + 1):
            email = f"docente{i}@seed.local"
            username = f"docente{i}"

            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "nombre": f"Docente {i}",
                    "rol": "docente",
                    "activo": True,
                },
            )

            if was_created:
                user.set_password("Pass1234!")
                user.save(update_fields=["password"])
                created += 1

        return created

    def _create_materias_y_grupos(self, ciclo):
        docentes = list(User.objects.filter(
            rol="docente", activo=True).order_by("id"))
        if not docentes:
            raise ValueError(
                "No hay docentes disponibles para asignar grupos.")

        materias_base = [
            ("Matematicas", "MAT"),
            ("Historia", "HIS"),
            ("Fisica", "FIS"),
            ("Quimica", "QUI"),
            ("Biologia", "BIO"),
            ("Lengua", "LEN"),
            ("Geografia", "GEO"),
            ("Programacion", "PRO"),
        ]

        materias_created = 0
        for idx, (nombre, clave_base) in enumerate(materias_base, start=1):
            clave = f"{clave_base}-{ciclo.id}"
            materia, materia_created = Materia.objects.get_or_create(
                nombre=nombre,
                clave=clave,
                ciclo=ciclo,
            )
            if materia_created:
                materias_created += 1

            docente = docentes[(idx - 1) % len(docentes)]
            Grupo.objects.update_or_create(
                codigo=f"GRP-{ciclo.id}-{idx:02d}",
                defaults={
                    "nombre": f"{nombre} - Grupo {idx}",
                    "materia": materia,
                    "docente": docente,
                    "ciclo": ciclo,
                },
            )

        return materias_created

    def _create_students_and_enrollments(self, count, ciclo):
        groups = list(Grupo.objects.filter(
            ciclo=ciclo).select_related("materia"))
        if not groups:
            raise ValueError(
                "No hay grupos disponibles para inscribir alumnos.")

        students_created = 0
        enrollments_created = 0

        for i in range(1, count + 1):
            email = f"alumno{i}@seed.local"
            username = f"alumno{i}"

            alumno, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "nombre": f"Alumno {i}",
                    "rol": "alumno",
                    "matricula": 20260000 + i,
                    "activo": True,
                },
            )

            if was_created:
                alumno.set_password("Pass1234!")
                alumno.save(update_fields=["password"])
                students_created += 1

            sample_size = random.randint(2, min(4, len(groups)))
            selected_groups = random.sample(groups, sample_size)
            for group in selected_groups:
                _, created = Inscripcion.objects.get_or_create(
                    alumno=alumno,
                    grupo=group,
                    materia=group.materia,
                    ciclo=ciclo,
                )
                if created:
                    enrollments_created += 1

        return students_created, enrollments_created
