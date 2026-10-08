import time

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    'cloud_office_http_requests_total',
    'Total HTTP requests handled by Django.',
    ('method', 'path', 'status'),
)
HTTP_LATENCY = Histogram(
    'cloud_office_http_request_duration_seconds',
    'HTTP request latency in seconds.',
    ('method', 'path'),
)


def observe_request(get_response):
    def middleware(request):
        started = time.perf_counter()
        response = get_response(request)
        path = request.path[:200]
        status = str(response.status_code)
        HTTP_REQUESTS.labels(request.method, path, status).inc()
        HTTP_LATENCY.labels(request.method, path).observe(time.perf_counter() - started)
        return response

    return middleware
