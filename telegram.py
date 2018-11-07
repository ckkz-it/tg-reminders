from django.conf import settings
import logging
import django
import os

from core.telegram_api import TelegramBot

os.environ['DJANGO_SETTINGS_MODULE'] = 'reminders.settings'
django.setup()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

tg = TelegramBot(settings.TELEGRAM_TOKEN)
