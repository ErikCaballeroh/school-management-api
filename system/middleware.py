"""
Middleware del sistema.

- RequestIDMiddleware: asigna un X-Request-ID unico a cada peticion (lo respeta
  si el cliente o el balanceador ya lo enviaron). Sirve para correlacionar
  logs entre la instancia, el load balancer (Nginx) y el cliente.

- RequestMetricsMiddleware: mide la duracion de cada peticion, registra en el
  store de metricas y agrega los headers X-Response-Time-MS y X-Server-Instance.

- HealthCheckBypassMiddleware: responde inmediatamente a /healthz sin pasar por
  autenticacion/DB para que el load balancer pueda hacer liveness checks
  baratos.
"""

import logging
import os
import socket
import time
import uuid

from django.http import JsonResponse

from .metrics import metrics


logger = logging.getLogger('system.requests')

INSTANCE_ID = os.getenv('INSTANCE_ID') or socket.gethostname()


class RequestIDMiddleware:
    HEADER = 'HTTP_X_REQUEST_ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get(self.HEADER) or uuid.uuid4().hex
        request.request_id = rid
        response = self.get_response(request)
        response['X-Request-ID'] = rid
        return response


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        route = self._normalize_route(request.path)
        metrics.record(
            route=route,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response['X-Response-Time-MS'] = f'{duration_ms:.2f}'
        response['X-Server-Instance'] = INSTANCE_ID

        logger.info(
            'rid=%s instance=%s %s %s -> %s in %.2fms',
            getattr(request, 'request_id', '-'),
            INSTANCE_ID,
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response

    @staticmethod
    def _normalize_route(path):
        # Colapsa IDs numericos para que /api/grupos/1/ y /api/grupos/2/
        # cuenten como la misma ruta en las metricas.
        parts = []
        for seg in path.split('/'):
            if seg.isdigit():
                parts.append(':id')
            else:
                parts.append(seg)
        return '/'.join(parts) or '/'


class HealthCheckBypassMiddleware:
    """Responde 200 a /healthz sin tocar DB ni auth — para liveness probes."""

    PATHS = {'/healthz', '/healthz/'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in self.PATHS:
            return JsonResponse({
                'status': 'ok',
                'instance': INSTANCE_ID,
            })
        return self.get_response(request)
