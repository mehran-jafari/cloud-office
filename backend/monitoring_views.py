import hmac

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def metrics(request):
    expected = settings.METRICS_TOKEN
    if expected:
        provided = request.headers.get('Authorization', '')
        if not hmac.compare_digest(provided, f'Bearer {expected}'):
            return JsonResponse({'detail': 'metrics authentication required'}, status=401)
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
