"""
Utilidades de procesamiento paralelo para los reportes.

`run_parallel` decide entre ProcessPoolExecutor (verdadero paralelismo CPU,
escala con nucleos del servidor) y ThreadPoolExecutor (I/O bound, comparte el
ORM de Django sin overhead de pickling).

`cached_report` cachea la respuesta JSON de un reporte por una ventana corta.
Funciona con cualquier backend de cache configurado (locmem por defecto,
Redis en produccion). Esto hace los reportes escalables: una segunda peticion
identica responde sin recomputar.
"""

import hashlib
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import wraps

from django.core.cache import cache
from django.db import connections


logger = logging.getLogger('system.parallel')

DEFAULT_WORKERS = max(2, (os.cpu_count() or 2))


def _close_connections():
    """Cierra conexiones DB heredadas — necesario en cada worker de proceso."""
    for conn in connections.all():
        conn.close()


def run_parallel(func, items, *, mode='thread', max_workers=None):
    """
    Ejecuta `func(item)` para cada item en paralelo.

    mode='thread' usa hilos (compatibles con el ORM, ideal para I/O).
    mode='process' usa procesos (escala con cores, requiere func/items
    serializables y que func cierre sus propias conexiones).
    """
    workers = max_workers or DEFAULT_WORKERS
    if mode == 'process':
        executor_cls = ProcessPoolExecutor
        kwargs = {'initializer': _close_connections}
    else:
        executor_cls = ThreadPoolExecutor
        kwargs = {}

    results = []
    with executor_cls(max_workers=workers, **kwargs) as executor:
        futures = [executor.submit(func, item) for item in items]
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception:
                logger.exception('parallel task failed')
                raise
            results.append(result)
    return results


def cached_report(prefix, ttl_seconds=60):
    """
    Cachea el valor de retorno (debe ser serializable como JSON) por `ttl_seconds`.
    La clave incluye el prefijo y los argumentos posicionales y nombrados.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            raw_key = json.dumps([prefix, args, sorted(kwargs.items())], default=str)
            key = f'report:{prefix}:{hashlib.md5(raw_key.encode()).hexdigest()}'

            cached = cache.get(key)
            if cached is not None:
                logger.info('cache hit key=%s', key)
                return {**cached, 'cached': True}

            value = fn(*args, **kwargs)
            try:
                cache.set(key, value, timeout=ttl_seconds)
            except Exception:
                logger.exception('cache set failed key=%s', key)
            return {**value, 'cached': False}
        return wrapper
    return decorator
