from django.conf import settings

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Dispatcher
from telegram import Bot
from telegram.utils.request import Request

import logging

logger = logging.getLogger('main')


class TelegramBot(object):

    def __init__(self, token):
        request = Request(proxy_url=settings.TELEGRAM_PROXY_URL,
                          urllib3_proxy_kwargs={
                              'username': settings.TELEGRAM_PROXY_USER,
                              'password': settings.TELEGRAM_PROXY_PASSWORD
                          })
        self.bot = Bot(token=token, request=request)
        self.dispatcher = Dispatcher(self.bot, None, workers=0)

    def setup(self):
        self.__setup_webhook()
        self.__setup_handlers()

    def __setup_webhook(self):
        self.bot.set_webhook(settings.TELEGRAM_HOOK_URL)

    def __setup_handlers(self):
        handler = MessageHandler(Filters.text | Filters.command, self.handle_message)
        self.dispatcher.add_handler(handler)

    @staticmethod
    def unknown(bot, update):
        bot.send_message(chat_id=update.message.chat_id, text='Sorry, I didn\'t understand that command.')

    def handle_message(self, update):
        logger.info(f'Received: {update.message}')
        chat_id = update.message.chat_id
        if update.message.text == '/start':
            self.unknown(self.bot, update)
