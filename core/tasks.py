from django.conf import settings
from django.db.models import F

import celery
import logging
import json
import arrow

from celery.signals import worker_ready

from telegram import Update

from reminders.celery import app
from core.telegram_api import TelegramBot
from core.models import Reminder

logger = logging.getLogger(__name__)

tg = None


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
    max_retries = 3
    ignore_result = True
    default_retry_delay = 10
    queue = 'main'

    def __init__(self):
        self.tg = tg

    def on_prerun(self, *args, **kwargs):
        try:
            if self.tg is None:
                logger.info('tg is None, setup it')
                self.setup_tg()
        except Exception as exc:
            self.retry(exc=exc)

    def setup_tg(self):
        logger.info('Telegram set up')
        self.tg = TelegramBot(settings.TELEGRAM_TOKEN)
        self.tg.setup()

    def run(self, *args, **kwargs):
        return super().run(*args, **kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        pass


class ProcessWebhook(BaseTask):

    def run(self, *args, **kwargs):
        logger.info('got webhook')
        update = Update.de_json(json.loads(kwargs['unicode_body']), self.tg.bot)
        self.tg.dispatcher.process_update(update)


class CheckReminders(BaseTask):
    def run(self, *args, **kwargs):
        logger.info('Starting check reminders')
        logger.info(self.tg)
        reminders = Reminder.objects.filter(
            date__lte=arrow.now('Europe/Moscow').datetime, done=False, processing=False
        )
        if not reminders:
            logger.info('No reminders to remind')
            return

        for reminder in reminders:
            if reminder.repeat_count:
                RemindByPeriod().apply_async(kwargs={'id': reminder.id})
                return

            text = 'Reminding you!'
            if reminder.message:
                text += f'\n{reminder.message}'
            self.tg.bot.send_message(chat_id=reminder.telegram_chat.telegram_id, text=text)
            reminder.done = True
            reminder.save()


class RemindByPeriod(BaseTask):
    def run(self, *args, **kwargs):
        reminder = Reminder.objects.get(id=kwargs['id'])
        reminder.processing = True
        reminder.repeat_count = F('repeat_count') - 1
        reminder.save()
        reminder.refresh_from_db()
        repeat_task = False
        if reminder.repeat_count > 0:
            repeat_task = True
        else:
            reminder.done = True
            reminder.processing = False
            reminder.save()

        text = 'Reminding you!'
        if reminder.message:
            text += f'\n{reminder.message}'
        self.tg.bot.send_message(chat_id=reminder.telegram_chat.telegram_id, text=text)
        if repeat_task:
            RemindByPeriod().apply_async(
                countdown=reminder.repeat_period * 60, kwargs={'id': reminder.id}
            )


app.tasks.register(CheckReminders())
app.tasks.register(ProcessWebhook())
app.tasks.register(RemindByPeriod())


@worker_ready.connect()
def setup_webhook(sender, **kwargs):
    logger.info('Worker ready')
    global tg
    tg = TelegramBot(settings.TELEGRAM_TOKEN)
    tg.setup()
