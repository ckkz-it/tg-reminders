from django.conf import settings
import django

import celery
import logging
import json

from celery.signals import worker_ready

from telegram import Update

from reminders.celery import app
from core.telegram_api import TelegramBot

logger = logging.getLogger(__name__)


def task_prerun(fn, prerun):
    def wrapped(*args, **kwargs):
        prerun(*args, **kwargs)
        return fn(*args, **kwargs)

    return wrapped


class MetaBaseTask(type):
    def __init__(cls, name, bases, attrs):
        cls.name = name
        cls.run = task_prerun(cls.run, getattr(cls, 'on_prerun'))
        super().__init__(cls)


class BaseTask(celery.Task, metaclass=MetaBaseTask):
    serializer = settings.CELERY_TASK_SERIALIZER
    # max_retries = settings.CELERY_MAX_RETRIES
    max_retries = 0
    ignore_result = True
    # default_retry_delay = settings.CELERY_RETRY_DELAY
    queue = 'main'

    def __init__(self):
        self.tg = None

    def on_prerun(self, *args, **kwargs):
        pass

    def run(self, *args, **kwargs):
        return super().run(*args, **kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        pass


class ProcessWebhook(BaseTask):
    def on_prerun(self, *args, **kwargs):
        if self.tg is None:
            logger.info('tg is None, setup it')
            self.setup_tg()

    def setup_tg(self):
        logger.info('Telegram set up')
        self.tg = TelegramBot(settings.TELEGRAM_TOKEN)
        self.tg.setup()

    def run(self, *args, **kwargs):
        logger.info('got webhook')
        logger.info(kwargs)
        update = Update.de_json(json.loads(kwargs['unicode_body']), self.tg.bot)
        self.tg.dispatcher.process_update(update)


class CheckReminders(BaseTask):
    def run(self, *args, **kwargs):
        logger.info('Starting check reminders')
        logger.info(self.tg)
        pass


app.tasks.register(CheckReminders())
app.tasks.register(ProcessWebhook())


@worker_ready.connect()
def setup_webhook(sender, **kwargs):
    logger.info('Worker ready')
    tg = TelegramBot(settings.TELEGRAM_TOKEN)
    tg.setup()
