from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from telegram import Update

import logging
import json

logger = logging.getLogger('main')


@require_POST
@csrf_exempt
def telegram_hook(request):
    from core.telegram_api import TelegramBot
    logger.info('webhook')
    tg = TelegramBot(settings.TELEGRAM_TOKEN)
    unicode_body = request.body.decode('utf-8')
    update = Update.de_json(json.loads(unicode_body), tg.bot)
    tg.handle_message(update)
    return HttpResponse('OK')
