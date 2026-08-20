"""
Prometheus-Metriken für Wachbuch (manuelle Implementierung als Ersatz für django-prometheus)
Kompatibel mit Django 6.1+
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import time


# Metriken definieren
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'path', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Duration in Seconds',
    ['method', 'path']
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Number of In-Progress HTTP Requests',
    ['method', 'path']
)

EXCEPTIONS_COUNT = Counter(
    'http_exceptions_total',
    'Total HTTP Exceptions',
    ['method', 'path', 'exception_type']
)


class PrometheusMiddleware(MiddlewareMixin):
    """Middleware für Prometheus-Metriken (kompatibel mit Django 6.1+)"""

    def process_request(self, request):
        # Ignoriere Metriken-Endpunkt
        if request.path == '/metrics/':
            return None

        method = request.method.lower()
        path = request.path

        # Inkrementiere In-Progress-Gauge
        REQUEST_IN_PROGRESS.labels(method=method, path=path).inc()

        # Starte Timer
        request._prometheus_start_time = time.time()

        return None

    def process_response(self, request, response):
        # Ignoriere Metriken-Endpunkt
        if hasattr(request, '_prometheus_prometheus_response'):
            return response

        if hasattr(request, '_prometheus_start_time'):
            method = request.method.lower()
            path = request.path
            status = str(response.status_code)

            # Messung beenden
            duration = time.time() - request._prometheus_start_time
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)

            # Inkrementiere Request-Counter
            REQUEST_COUNT.labels(method=method, path=path, status=status).inc()

            # Dekrementiere In-Progress-Gauge
            REQUEST_IN_PROGRESS.labels(method=method, path=path).dec()

        return response

    def process_exception(self, request, exception):
        if hasattr(request, '_prometheus_start_time'):
            method = request.method.lower()
            path = request.path
            exception_type = type(exception).__name__

            # Inkrementiere Exception-Counter
            EXCEPTIONS_COUNT.labels(
                method=method,
                path=path,
                exception_type=exception_type
            ).inc()

            # Dekrementiere In-Progress-Gauge
            REQUEST_IN_PROGRESS.labels(method=method, path=path).dec()

        return None


def metrics_view(request):
    """Prometheus-Metriken-Endpunkt"""
    request._prometheus_prometheus_response = True
    return HttpResponse(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST
    )
