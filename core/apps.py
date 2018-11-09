from django.apps import AppConfig
from django.conf import settings
from time import sleep

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('MAIN')

tg = None


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from core.telegram_api import TelegramBot
        logger.info('Telegram set up')
        global tg
        tg = TelegramBot(settings.TELEGRAM_TOKEN)
        tg.setup()
        sleep(1)
