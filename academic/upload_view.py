import logging
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from system.resilience import CircuitBreakerOpen, r2_breaker, retry


logger = logging.getLogger('academic.upload')

ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'pptx', 'xlsx', 'jpg', 'jpeg', 'png', 'zip', 'rar',
}
FORBIDDEN_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv'}
MAX_BYTES = 30 * 1024 * 1024  # 30 MB segun spec v2.1 seccion 5


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES['file']
        ext = (file_obj.name.rsplit('.', 1)[-1] if '.' in file_obj.name else '').lower()

        if ext in FORBIDDEN_EXTENSIONS:
            return Response(
                {
                    'error': (
                        'Archivos de video no permitidos. Sube un enlace de '
                        'YouTube o Google Drive en el campo de video.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ext not in ALLOWED_EXTENSIONS:
            return Response(
                {
                    'error': (
                        f'Extension ".{ext}" no permitida. Tipos validos: '
                        f'{", ".join(sorted(ALLOWED_EXTENSIONS))}.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file_obj.size > MAX_BYTES:
            return Response(
                {
                    'error': (
                        f'Archivo demasiado grande ({file_obj.size} bytes). '
                        f'Maximo permitido: {MAX_BYTES} bytes (30 MB).'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not all([
            settings.R2_ACCOUNT_ID,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
        ]):
            return Response(
                {'error': 'Servidor no configurado correctamente para cargar archivos.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        s3 = boto3.client(
            's3',
            endpoint_url=f'https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name='auto',
        )

        unique_filename = f'{uuid.uuid4()}.{ext}'

        def _do_upload():
            file_obj.seek(0)
            s3.upload_fileobj(
                file_obj,
                settings.R2_BUCKET_NAME,
                unique_filename,
                ExtraArgs={'ContentType': file_obj.content_type},
            )

        try:
            r2_breaker.call(
                lambda: retry(
                    _do_upload,
                    attempts=3,
                    base_delay=0.3,
                    exceptions=(BotoCoreError, ClientError),
                )
            )
        except CircuitBreakerOpen:
            return Response(
                {
                    'error': (
                        'El servicio de almacenamiento no esta disponible '
                        'temporalmente. Intenta de nuevo en unos segundos.'
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception('R2 upload failed: %s', exc)
            return Response(
                {'error': 'Fallo al subir el archivo al almacenamiento.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if settings.R2_CUSTOM_DOMAIN:
            file_url = f"{settings.R2_CUSTOM_DOMAIN.rstrip('/')}/{unique_filename}"
        else:
            file_url = (
                f'https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com/'
                f'{settings.R2_BUCKET_NAME}/{unique_filename}'
            )

        return Response(
            {
                'url': file_url,
                'nombre_archivo': file_obj.name,
                'tamano_bytes': file_obj.size,
            },
            status=status.HTTP_201_CREATED,
        )
