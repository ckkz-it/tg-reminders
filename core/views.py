from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .tasks import logger, ProcessWebhook


@require_POST
@csrf_exempt
def telegram_hook(request):
    logger.info('webhook')
    unicode_body = request.body.decode('utf-8')
    ProcessWebhook().delay(unicode_body=unicode_body)
    return HttpResponse('OK')
