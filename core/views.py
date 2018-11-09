from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from telegram import Update

import logging
import json

from .apps import tg

logger = logging.getLogger('MAIN')


@require_POST
@csrf_exempt
def telegram_hook(request):
    logger.info('webhook')
    unicode_body = request.body.decode('utf-8')
    update = Update.de_json(json.loads(unicode_body), tg.bot)
    tg.dispatcher.process_update(update)
    return HttpResponse('OK')
