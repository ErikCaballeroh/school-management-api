"""
Primitivas de tolerancia a fallos.

- retry: reintenta una callable con backoff exponencial.
- CircuitBreaker: corta llamadas a un servicio externo cuando falla
  repetidamente, y vuelve a probarlo despues de un cooldown (estado HALF_OPEN).

Se usan para envolver operaciones contra servicios externos (Cloudflare R2) y
contra la BD cuando una conexion se cae. El estado de cada breaker se publica
en system.metrics para que el dashboard de monitoreo lo muestre.
"""

import logging
import random
import time
from threading import RLock

from .metrics import metrics


logger = logging.getLogger('system.resilience')


def retry(func, *, attempts=3, base_delay=0.2, max_delay=2.0, exceptions=(Exception,)):
    """Reintenta `func` con backoff exponencial + jitter."""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except exceptions as exc:
            last_exc = exc
            if attempt == attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)
            logger.warning(
                'retry %d/%d after error=%s sleeping=%.2fs',
                attempt, attempts, exc, delay,
            )
            time.sleep(delay)
    raise last_exc


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(self, name, failure_threshold=5, recovery_timeout=30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = self.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._lock = RLock()
        self._publish()

    def _publish(self):
        metrics.set_circuit(self.name, {
            'state': self._state,
            'failures': self._failures,
            'opened_at': self._opened_at,
        })

    def call(self, func):
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._opened_at >= self.recovery_timeout:
                    self._state = self.HALF_OPEN
                    self._publish()
                    logger.info('breaker=%s half_open', self.name)
                else:
                    raise CircuitBreakerOpen(
                        f'Circuit breaker "{self.name}" is OPEN'
                    )

        try:
            result = func()
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_success(self):
        with self._lock:
            self._failures = 0
            if self._state != self.CLOSED:
                logger.info('breaker=%s closed', self.name)
            self._state = self.CLOSED
            self._opened_at = 0.0
            self._publish()

    def _on_failure(self):
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = self.OPEN
                self._opened_at = time.time()
                logger.warning(
                    'breaker=%s opened after %d failures',
                    self.name, self._failures,
                )
            self._publish()


# Breaker compartido para Cloudflare R2.
r2_breaker = CircuitBreaker('cloudflare_r2', failure_threshold=5, recovery_timeout=30.0)
