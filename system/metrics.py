"""
Almacen en memoria de metricas del sistema.

Usado por el middleware para recolectar latencias, conteos por ruta y por
estatus HTTP. Es thread-safe y de tamano acotado para no consumir memoria sin
limite. En un despliegue real estos datos se exportarian a Prometheus, pero
para el PIA basta con un agregador en proceso.
"""

from collections import defaultdict, deque
from threading import RLock
from time import time


class _MetricsStore:
    MAX_SAMPLES = 1000

    def __init__(self):
        self._lock = RLock()
        self._started_at = time()
        self._total_requests = 0
        self._error_requests = 0
        self._latencies_ms = deque(maxlen=self.MAX_SAMPLES)
        self._by_route = defaultdict(lambda: {
            'count': 0,
            'errors': 0,
            'total_ms': 0.0,
            'max_ms': 0.0,
        })
        self._by_status = defaultdict(int)
        self._circuit_state = {}

    def record(self, route, method, status_code, duration_ms):
        with self._lock:
            self._total_requests += 1
            self._latencies_ms.append(duration_ms)
            self._by_status[str(status_code)] += 1
            if status_code >= 500:
                self._error_requests += 1

            key = f'{method} {route}'
            entry = self._by_route[key]
            entry['count'] += 1
            entry['total_ms'] += duration_ms
            if duration_ms > entry['max_ms']:
                entry['max_ms'] = duration_ms
            if status_code >= 500:
                entry['errors'] += 1

    def set_circuit(self, name, state):
        with self._lock:
            self._circuit_state[name] = state

    def snapshot(self):
        with self._lock:
            samples = list(self._latencies_ms)
            samples_sorted = sorted(samples)
            n = len(samples_sorted)

            def pct(p):
                if n == 0:
                    return 0.0
                idx = min(n - 1, int(round(p * (n - 1))))
                return round(samples_sorted[idx], 2)

            avg_ms = round(sum(samples) / n, 2) if n else 0.0

            top_routes = sorted(
                (
                    {
                        'route': k,
                        'count': v['count'],
                        'errors': v['errors'],
                        'avg_ms': round(v['total_ms'] / v['count'], 2),
                        'max_ms': round(v['max_ms'], 2),
                    }
                    for k, v in self._by_route.items()
                ),
                key=lambda r: r['count'],
                reverse=True,
            )[:15]

            return {
                'uptime_seconds': round(time() - self._started_at, 2),
                'total_requests': self._total_requests,
                'error_requests': self._error_requests,
                'error_rate': (
                    round(self._error_requests / self._total_requests, 4)
                    if self._total_requests
                    else 0.0
                ),
                'latency_ms': {
                    'avg': avg_ms,
                    'p50': pct(0.5),
                    'p95': pct(0.95),
                    'p99': pct(0.99),
                    'samples': n,
                },
                'by_status': dict(self._by_status),
                'top_routes': top_routes,
                'circuits': dict(self._circuit_state),
            }


metrics = _MetricsStore()
