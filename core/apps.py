from django.apps import AppConfig
from django.conf import settings
from time import sleep

import logging

logger = logging.getLogger('core.tasks')


# tg = None


class CoreConfig(AppConfig):
    name = 'core'

    # def ready(self):
    #     from core.telegram_api import TelegramBot
    #     logger.info('Telegram set up')
    #     global tg
    #     tg = TelegramBot(settings.TELEGRAM_TOKEN)
    #     tg.setup()
    #     sleep(1)
