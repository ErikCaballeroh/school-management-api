"""
Endpoints de monitoreo del sistema (PIA: Monitoreo de Recursos).

- /api/system/health/   liveness + readiness (chequea DB y cache)
- /api/system/metrics/  metricas agregadas (latencias, top routes, breakers)
- /api/system/resources/ recursos del host (CPU, RAM, disco, procesos)
- /api/system/info/     info de la instancia (workers, python, host)

El endpoint /healthz (sin /api/) lo sirve HealthCheckBypassMiddleware para
liveness rapidos del load balancer.
"""

import os
import platform
import socket
import sys
import time

from django.core.cache import cache
from django.db import connection, OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .metrics import metrics


try:
    import psutil
    HAS_PSUTIL = True
except ImportError:  # psutil es opcional pero recomendado
    HAS_PSUTIL = False


INSTANCE_ID = os.getenv('INSTANCE_ID') or socket.gethostname()
_BOOT_TIME = time.time()


def _check_db():
    start = time.perf_counter()
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        return {
            'ok': True,
            'latency_ms': round((time.perf_counter() - start) * 1000.0, 2),
        }
    except OperationalError as exc:
        return {'ok': False, 'error': str(exc)}


def _check_cache():
    try:
        cache.set('healthz', 'ok', timeout=5)
        ok = cache.get('healthz') == 'ok'
        return {'ok': ok}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    """Readiness: usado por Nginx upstream para sacar instancias enfermas."""
    db = _check_db()
    cache_status = _check_cache()
    healthy = db['ok'] and cache_status['ok']
    payload = {
        'status': 'ok' if healthy else 'degraded',
        'instance': INSTANCE_ID,
        'uptime_seconds': round(time.time() - _BOOT_TIME, 2),
        'checks': {'database': db, 'cache': cache_status},
    }
    return Response(payload, status=200 if healthy else 503)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_metrics(request):
    """Metricas agregadas del proceso (latencias, conteos, breakers)."""
    return Response({
        'instance': INSTANCE_ID,
        **metrics.snapshot(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_resources(request):
    """Snapshot de recursos del host (CPU, RAM, disco)."""
    if not HAS_PSUTIL:
        return Response({
            'instance': INSTANCE_ID,
            'available': False,
            'error': 'psutil no esta instalado en el servidor.',
        }, status=503)

    cpu_pct = psutil.cpu_percent(interval=0.2)
    cpu_per_core = psutil.cpu_percent(interval=0.0, percpu=True)
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    disk = psutil.disk_usage('/')
    load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

    return Response({
        'instance': INSTANCE_ID,
        'available': True,
        'cpu': {
            'percent': cpu_pct,
            'cores': psutil.cpu_count(logical=True),
            'physical_cores': psutil.cpu_count(logical=False),
            'per_core_percent': cpu_per_core,
            'load_avg': {'1m': load[0], '5m': load[1], '15m': load[2]},
        },
        'memory': {
            'total_mb': round(vm.total / 1024 / 1024, 2),
            'used_mb': round(vm.used / 1024 / 1024, 2),
            'available_mb': round(vm.available / 1024 / 1024, 2),
            'percent': vm.percent,
        },
        'swap': {
            'total_mb': round(sm.total / 1024 / 1024, 2),
            'used_mb': round(sm.used / 1024 / 1024, 2),
            'percent': sm.percent,
        },
        'disk': {
            'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
            'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'percent': disk.percent,
        },
        'process': {
            'pid': os.getpid(),
            'threads': psutil.Process().num_threads(),
            'memory_mb': round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_info(request):
    return Response({
        'instance': INSTANCE_ID,
        'hostname': socket.gethostname(),
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'pid': os.getpid(),
        'workers_env': os.getenv('GUNICORN_WORKERS', 'n/a'),
        'cache_backend': os.getenv('CACHE_BACKEND', 'locmem'),
        'started_at': _BOOT_TIME,
    })
