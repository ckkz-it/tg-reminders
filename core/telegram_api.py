from django.conf import settings

from telegram.ext import Dispatcher
from telegram import Bot
from telegram.utils.request import Request

import logging

logger = logging.getLogger('MAIN')


class TelegramBot(object):
    def __init__(self, token):
        from .handlers import TelegramHandlers

        request = Request(proxy_url=settings.TELEGRAM_PROXY_URL,
                          urllib3_proxy_kwargs={
                              'username': settings.TELEGRAM_PROXY_USER,
                              'password': settings.TELEGRAM_PROXY_PASSWORD
                          })
        self.tg_handlers = TelegramHandlers()
        self.bot = Bot(token=token, request=request)
        self.dispatcher = Dispatcher(self.bot, None)

    def setup(self):
        self.__setup_handlers()
        self.__setup_webhook()

    def __setup_webhook(self):
        self.bot.set_webhook(settings.TELEGRAM_HOOK_URL)

    def __setup_handlers(self):
        for handler in self.tg_handlers.get_handlers():
            self.dispatcher.add_handler(handler)


class Message(object):
    def __init__(self, body, **options):
        self.body = body
        self.options = options


class Markdown(Message):
    def __init__(self, body: object, options: object) -> object:
        super(Markdown, self).__init__(body, parse_mode="Markdown", **options)


class HTML(Message):
    def __init__(self, body, **options):
        super(HTML, self).__init__(body, parse_mode="HTML", **options)
