import uuid
import boto3
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['file']

        # Validar variables de entorno (Opcional, pero recomendado)
        if not all([settings.R2_ACCOUNT_ID, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY, settings.R2_BUCKET_NAME]):
            return Response({'error': 'Servidor no configurado correctamente para cargar archivos.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        s3 = boto3.client('s3',
                          endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                          aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                          region_name='auto'
                          )

        file_extension = file_obj.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        try:
            s3.upload_fileobj(
                file_obj,
                settings.R2_BUCKET_NAME,
                unique_filename,
                ExtraArgs={
                    "ContentType": file_obj.content_type
                }
            )

            # Si tienes un dominio personalizado vinculado a tu bucket R2, devuélvelo
            if settings.R2_CUSTOM_DOMAIN:
                file_url = f"{settings.R2_CUSTOM_DOMAIN.rstrip('/')}/{unique_filename}"
            else:
                # Si no, devuelve la ruta relativa (aunque no puedes acceder a la URL principal, lo ideal es tener public access custom domain configurado)
                file_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{settings.R2_BUCKET_NAME}/{unique_filename}"

            return Response({'url': file_url}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
